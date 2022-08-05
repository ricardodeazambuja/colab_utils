"""colab_utils: Some useful (or not so much) Python stuff for Google Colab notebooks

Copyright (C) 2020 Ricardo de Azambuja

colab_utils is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

colab_utils is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with colab_utils.  If not, see <https://www.gnu.org/licenses/>.

Acknowledgement:
This work was possible thanks to the financial support from IVADO.ca (postdoctoral scholarship 2019/2020).

Disclaimer (adapted from Wikipedia):
None of the authors, contributors, supervisors, administrators, employers, friends, family, vandals, or anyone else 
connected (or not) with this project, in any way whatsoever, can be made responsible for your use of the information (code) 
contained or linked from here.
"""

from IPython.display import display, Javascript, HTML, Audio
from io import BytesIO
from base64 import b64encode, b64decode
from uuid import uuid4
import requests
from time import sleep
import json
from os.path import join, isdir, isfile
from os import mkdir

from google.colab.output import eval_js
from PIL import Image, ImageDraw, ImageOps, ImageEnhance
import numpy as np
from scipy.io.wavfile import read as wav_read
import ffmpeg


def webcam2numpy(quality=0.8, size=(800,600)):
  """Saves images from your webcam into a numpy array.

  Returns
  -------
  numpy.ndarray
  """

  VIDEO_HTML = """
  <div class="video_container">
    <video autoplay
    width=%d height=%d></video>
    <div style='position: absolute;top: 40px; left: 40px; font-size: 40px; color: green;'>Click on the image to save!</div>
  </div>

  <script>

  var video = document.querySelector('video')

  navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream=> video.srcObject = stream)
    
  var data = new Promise(resolve=>{
    video.onclick = ()=>{
      var canvas = document.createElement('canvas')
      var [w,h] = [video.offsetWidth, video.offsetHeight]
      canvas.width = w
      canvas.height = h
      canvas.getContext('2d')
            .drawImage(video, 0, 0, w, h)
      video.srcObject.getVideoTracks()[0].stop()
      video.replaceWith(canvas)
      resolve(canvas.toDataURL('image/jpeg', %f))
    }
  })
  </script>
  """

  handle = display(HTML(VIDEO_HTML % (size[0],size[1],quality)), display_id='videoHTML')
  data = eval_js("data")
  binary = b64decode(data.split(',')[1])
  f = BytesIO(binary)
  return np.asarray(Image.open(f))

  

def labelImage(inputImg, imgformat='PNG', deleteAfter=True, scale = 1.0, line_color="green"):
  """Opens an image, record mouse clicks (boxes) and labels.

  Returns
  -------
  list
     [box (list), label (str)]

  """

  JS_SRC = """
    async function label_image(scale) {
      const image  = document.getElementById("inputImage");
      const w = image.width;
      const h = image.height;

      const image_div = document.getElementById("image_div");

      const ok_btn = document.createElement('button');
      ok_btn.textContent = 'Finish';
      const add_btn = document.createElement('button');
      add_btn.textContent = 'Add';
      const clr_btn = document.createElement('button');
      clr_btn.textContent = 'Clear';
      const textbox = document.createElement('input');
      textbox.textContent = "text";

      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;

      var ctx = canvas.getContext('2d');
      canvas.style.position = 'absolute';
      canvas.style.left = '0px';
      canvas.style.top = '0px';
      canvas.style.z_index = 1000;
      canvas.style.border = 0;
      canvas.style.padding = 0;
      canvas.style.margin = 0;

      //ctx.fillStyle = "blue";
      //ctx.fillRect(0, 0, canvas.width, canvas.height);

      image_div.appendChild(canvas);

      const interface_div = document.getElementById("interface_div");
      interface_div.appendChild(textbox);
      interface_div.appendChild(add_btn);
      interface_div.appendChild(ok_btn);
      interface_div.appendChild(clr_btn);

      textbox.width = 100;

      var x1,x2,y1,y2;

      var clickNumber = 0;

      var boxes = new Array();

      var try_again = true;
      
      while (try_again){
      await new Promise((resolve) => {
        canvas.onclick = () => {
            console.log("X:"+event.clientX+" Y:"+event.clientY); 
            if(clickNumber==0){
                            x1 = event.clientX;
                            y1 = event.clientY;
                            clickNumber = 1;
            }else if(clickNumber==1){
                            x2 = event.clientX;
                            y2 = event.clientY;
                            ctx.lineWidth = 5;
                            ctx.strokeStyle = '%s';
                            ctx.strokeRect(x1, y1, x2-x1, y2-y1);
                            clickNumber = 2;
            }
            resolve();
            };
        ok_btn.onclick = () => {try_again=false; 
                                boxes.push([[x1/w, y1/h, (x2-x1)/w, (y2-y1)/h],textbox.value]);
                                if("%s" == "True"){
                                  tmp_div = document.getElementById("main_div");
                                  tmp_div.remove();
                                }
                                resolve();
                                };
        add_btn.onclick = () => {
                                if (clickNumber==2){
                                boxes.push([[x1/w, y1/h, (x2-x1)/w, (y2-y1)/h],textbox.value]);
                                clickNumber = 0;
                                }
                                resolve();
                                };
        clr_btn.onclick = () => { 
                                 ctx.clearRect(0, 0, canvas.width, canvas.height); 
                                 boxes = new Array();
                                 clickNumber = 0;
                                 resolve();
                                 };
        });
      
      }
      
      return boxes;
    }
    """ % (line_color,str(deleteAfter))
  
  imageBuffer = BytesIO()

  if type(inputImg) == str:
    img = Image.open(inputImg)
    w,h = img.size
    img.save(imageBuffer, format=imgformat)
  elif type(inputImg) == np.ndarray:
    img = Image.fromarray(inputImg)
    w,h = img.size
    img.save(imageBuffer, format=imgformat)
  elif "PIL" in str(type(inputImg)):
    w,h,_ = inputImg.size
    inputImg.save(imageBuffer, format=imgformat)

  imgBase64 = b64encode(imageBuffer.getvalue())
  if imgformat == 'PNG':
    str_data = "data:image/png;base64," + imgBase64.decode(encoding="utf-8")
  elif imgformat == 'JPEG' or imgformat == 'JPG':
    str_data = "data:image/jpeg;base64," + imgBase64.decode(encoding="utf-8")
  elif imgformat == 'GIF':
    str_data = "data:image/gif;base64," + imgBase64.decode(encoding="utf-8")
  else:
    raise "Wrong image format!"

  HTML_SRC = f"""
  <div id="main_div" style="padding:0; margin:0; border:0; height:{h*scale+50}px; width:{w*scale}px;">
  <div id="image_div" style="padding:0; margin:0; border:0; height:{h*scale}px; width:{w*scale}px; position:absolute; top:0px; left:0px;">
  <img id="inputImage" src="{str_data}" style="padding:0; margin:0; border:0; position:absolute; top:0px; left:0px;" height={h*scale}px; width={w*scale}px;/>
  </div>
  <div id="interface_div" style="padding:0; margin:0; border:0; position:absolute; top:{h*scale}px; left:0px;"></div>
  </div>
  """
  display(HTML(HTML_SRC))
  display(Javascript(JS_SRC))
  data = eval_js(f'label_image({float(scale)})')
  return data


def showAnnotations(img, annotations, color="green", line_width=2):
  """Draw the annotations generated by labelImage on the input image.
  """

  if type(img) == str:
    img = Image.open(img)
  elif type(img) == np.ndarray:
    img = Image.fromarray(img)
  elif "PIL" in str(type(img)):
    img = img.copy()
  else:
    ValueError("Image format not recognized!")
  
  w,h = img.size
  draw = ImageDraw.Draw(img)
  for annotation in annotations:
    text = annotation[1]
    annotation = annotation[0]
    draw.rectangle([annotation[0]*w, annotation[1]*h, (annotation[0]+annotation[2])*w, (annotation[1]+annotation[3])*h], fill=None, outline=color, width=line_width)
    draw.text((min((annotation[0],annotation[0]+annotation[2]))*w+2, min((annotation[1],annotation[1]+annotation[3]))*h+2), str(text), fill=color)
  
  return img


def getAudio():
  """Records audio from your local microphone inside a colab notebook

  Returns
  -------
  tuple
    audio (numpy.ndarray), sample rate (int)

  Obs:
  To write this piece of code I took inspiration/code from a lot of places.
  It was late night, so I'm not sure how much I created or just copied o.O
  Here are some of the possible references:
  https://blog.addpipe.com/recording-audio-in-the-browser-using-pure-html5-and-minimal-javascript/
  https://stackoverflow.com/a/18650249
  https://hacks.mozilla.org/2014/06/easy-audio-capture-with-the-mediarecorder-api/
  https://air.ghost.io/recording-to-an-audio-file-using-html5-and-js/
  https://stackoverflow.com/a/49019356
  """

  AUDIO_HTML = """
  <script>
  var my_div = document.createElement("DIV");
  var my_p = document.createElement("P");
  var my_btn = document.createElement("BUTTON");
  var t = document.createTextNode("Press to start recording");

  my_btn.appendChild(t);
  //my_p.appendChild(my_btn);
  my_div.appendChild(my_btn);
  document.body.appendChild(my_div);

  var base64data = 0;
  var reader;
  var recorder, gumStream;
  var recordButton = my_btn;

  var handleSuccess = function(stream) {
    gumStream = stream;
    var options = {
      //bitsPerSecond: 8000, //chrome seems to ignore, always 48k
      mimeType : 'audio/webm;codecs=opus'
      //mimeType : 'audio/webm;codecs=pcm'
    };            
    //recorder = new MediaRecorder(stream, options);
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = function(e) {            
      var url = URL.createObjectURL(e.data);
      var preview = document.createElement('audio');
      preview.controls = true;
      preview.src = url;
      document.body.appendChild(preview);

      reader = new FileReader();
      reader.readAsDataURL(e.data); 
      reader.onloadend = function() {
        base64data = reader.result;
        //console.log("Inside FileReader:" + base64data);
      }
    };
    recorder.start();
    };

  recordButton.innerText = "Recording... press to stop";

  navigator.mediaDevices.getUserMedia({audio: true}).then(handleSuccess);


  function toggleRecording() {
    if (recorder && recorder.state == "recording") {
        recorder.stop();
        gumStream.getAudioTracks()[0].stop();
        recordButton.innerText = "Saving the recording... pls wait!"
    }
  }

  // https://stackoverflow.com/a/951057
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  var data = new Promise(resolve=>{
  //recordButton.addEventListener("click", toggleRecording);
  recordButton.onclick = ()=>{
  toggleRecording()

  sleep(2000).then(() => {
    // wait 2000ms for the data to be available...
    // ideally this should use something like await...
    //console.log("Inside data:" + base64data)
    resolve(base64data.toString())

  });

  }
  });
        
  </script>
  """

  display(HTML(AUDIO_HTML))
  data = eval_js("data")
  binary = b64decode(data.split(',')[1])
  
  process = (ffmpeg
    .input('pipe:0')
    .output('pipe:1', format='wav')
    .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True, quiet=True, overwrite_output=True)
  )
  output, err = process.communicate(input=binary)
  
  riff_chunk_size = len(output) - 8
  # Break up the chunk size into four bytes, held in b.
  q = riff_chunk_size
  b = []
  for i in range(4):
      q, r = divmod(q, 256)
      b.append(r)

  # Replace bytes 4:8 in proc.stdout with the actual size of the RIFF chunk.
  riff = output[:4] + bytes(b) + output[8:]

  sr, audio = wav_read(BytesIO(riff))

  return audio, sr


def copy2clipboard(inputFile):
  """Opens a file or URL and copies the content to the clipboard.
  """

  js1 = """
  const tmp_div = document.createElement('div');
  const tmp_button = document.createElement('button');
  tmp_button.textContent = 'Copy2Clipboard';
  document.body.appendChild(tmp_div);
  tmp_div.appendChild(tmp_button);
  const inputTXT = atob("%s");
  const el = document.createElement('textarea');
  el.style.position = 'absolute';
  el.style.left = '-9999px';
  el.value = inputTXT;
  tmp_div.appendChild(el);


  async function copy2clipboard(){
    tmp_button.focus();
    await new Promise((resolve) => tmp_button.onclick = resolve);
    el.select();
    el.focus();
    document.execCommand('copy');
    el.remove()
    tmp_div.remove();
  }"""

  try:
    with open(inputFile, 'r') as file:
        data = file.read()
        data = b64encode(bytes(data, 'utf-8')).decode("utf-8")
  except FileNotFoundError:
      try:
          request = requests.get(inputFile)
          data = request.text
          data = b64encode(bytes(data, 'utf-8')).decode("utf-8")
      except (ConnectionError, requests.exceptions.MissingSchema) as e: 
          print('File / URL site does not exist')
          print(e)
          
  display(Javascript(js1 % data))
  display(Javascript("copy2clipboard()"))


def imshow(inputImg, imgformat="PNG", windowName="imwrite", width=None, height=None):
  """Shows an image using the same named window.
  """

  JS_SRC = """
    function testImage(windowName) {
      var image  = document.getElementById(windowName);

      if (typeof(image) != 'undefined' && image != null){
        return 1;
      } else {
        return 0;
      }
    }
      
    function imwrite(newSRC, windowName) {
      var image  = document.getElementById(windowName);

      if (typeof(image) != 'undefined' && image != null){
        console.log("image was NOT null");
        image.src = newSRC;
      } else {
        console.log("image was null");
        const image = document.createElement("image");
        image.id = windowName;
        document.body.appendChild(image);
      }

      //new Promise((resolve) => image.complete = resolve);

    }
    """
  
  imageBuffer = BytesIO()

  if type(inputImg) == str:
    save_all = False
    if imgformat == 'GIF':
      save_all = True
    Image.open(inputImg).save(imageBuffer, format=imgformat, save_all=save_all)
  elif type(inputImg) == np.ndarray:
    Image.fromarray(inputImg).save(imageBuffer, format=imgformat)
  elif "PIL" in str(type(inputImg)):
    inputImg.save(imageBuffer, format=imgformat)

  imgBase64 = b64encode(imageBuffer.getvalue())
  if imgformat == 'PNG':
    str_data = "data:image/png;base64," + imgBase64.decode(encoding="utf-8")
  elif imgformat == 'JPEG' or imgformat == 'JPG':
    str_data = "data:image/jpeg;base64," + imgBase64.decode(encoding="utf-8")
  elif imgformat == 'GIF':
    str_data = "data:image/gif;base64," + imgBase64.decode(encoding="utf-8")
  else:
    raise "Wrong image format!"

  display(Javascript(JS_SRC))

  if not eval_js('testImage("%s")' % windowName):
    HTML_SRC ="""
    <div id="%s_div">
    <img id="%s" src="%s" """ % (windowName, windowName, str_data)
    if width: 
      HTML_SRC += 'width="%s" ' % str(width)
    if height:
      HTML_SRC += 'height="%s" ' % str(height)
    HTML_SRC += "/><br></div>"
    
    display(HTML(HTML_SRC))

  display(Javascript("imwrite('%s','%s')" % (str_data, windowName)))



def videoGrabber(quality=0.8, size=(800,600), init_delay=100, showVideo=True):
  """Returns a video grabber object that saves images from your webcam into a PIL.Image object.
  Caveat: the returned video controller object can only be used inside the SAME cell because of sandboxing.
  
  Usage example:
    vid = videoGrabber()
    img_list = []
    for i in range(10):
      img_list.append(vid(10))
    vid(stop=True)
  """

  VIDEO_HTML = """
  <div id="video_container">
    <video autoplay
    width=%d height=%d></video>
  </div>

  <script>
  var video_div = document.getElementById("video_container");
  if(!%s){
    video_div.style.position = 'absolute';
    video_div.style.left = '-9999px';
  }
  var video = document.querySelector('video');
  var canvas = document.createElement('canvas');
  canvas.id = "canvas_container";

  var video_ready = false;

  const nav = navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
      video.srcObject = stream;
      sleep(%f).then(() => video_ready = true);
      });

  // https://stackoverflow.com/a/951057
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }


  function getData(ms){
    if(video_ready){
    return new Promise(resolve=>{
      sleep(ms).then(() => {
        var [w,h] = [video.offsetWidth, video.offsetHeight];
        canvas.width = w;
        canvas.height = h;
        canvas.getContext('2d').drawImage(video, 0, 0, w, h);
        resolve(canvas.toDataURL('image/jpeg', %f));
        });
      })
    }
  }


  function stopVideo(){
    video.srcObject.getVideoTracks()[0].stop();
    canvas.remove();
    video.remove();
    video_div.remove();
  }

  </script>
  """
  showVideo = "true" if showVideo else "false"
  handle = display(HTML(VIDEO_HTML % (size[0],size[1],showVideo,init_delay,quality)), display_id='videoHTML')

  def videoContr(ms=10, stop=False):
    if not stop:
      while True:
        data = eval_js("getData(%s)" % str(ms))        
        if data:
          binary = b64decode(data.split(',')[1])
          f = BytesIO(binary)
          return Image.open(f)
        else:
          sleep(0.1)
    else:
      eval_js("stopVideo()")
  
  return videoContr


def cocojson2modelmakercsv(cocojsonfilename, csvfilename, img_dir=""):
  """Convert COCO json annotations saved using VGG Via Annotator into
  TFLite Model Maker CSV format
  https://www.robots.ox.ac.uk/~vgg/software/via/via.html
  https://cloud.google.com/vision/automl/object-detection/docs/csv-format
  """
  with open(cocojsonfilename) as file:
    annot = json.load(file)

  csv_lines = [] # set,path,label,x_min,y_min,,,x_max,y_max,,
  for ann in annot['annotations']:
    label = annot['categories'][ann['category_id']-1]['name']
    img = annot['images'][ann['image_id']-1]
    try:
      path = img['coco_url']
    except KeyError as ke:
        path = img_dir + img['file_name']
    height = img['height']
    width = img['width']
    bbox = ann['bbox']
    x_min = bbox[0]/width
    x_max = (bbox[0]+bbox[2])/width
    y_min = bbox[1]/height
    y_max = (bbox[1]+bbox[3])/height

    csv_lines.append(f"UNASSIGNED,{path},{label},{x_min:0.2f},{y_min:0.2f},,,{x_max:0.2f},{y_max:0.2f},,")

  with open(csvfilename,"w") as file:
    file.write("\n".join(csv_lines)+"\n")


def saveimgslocally(csvfilename, newcsvfilename, img_path=""):
  """Download images from the TFLite Model Maker CSV
  and generate a new CSV file
  https://cloud.google.com/vision/automl/object-detection/docs/csv-format
  """
  if img_path:
    if not isdir(img_path):
      mkdir(img_path)
  with open(csvfilename,"r") as file:
    ds = file.read()

  img_i = 0
  last_url = ""
  img_name = ""
  new_ds = ""
  for i,l in enumerate(ds.splitlines()):
    url_fail = True
    print(f"Processing annotation #{i+1}")
    r = l.split(',')
    url = r[1]

    if url != last_url:
      img_i += 1
      img_name = join(img_path,f"image_{img_i}.jpg")

    if not isfile(img_name):
      if url != last_url:
        print(f"Downloading {url}")
        try: 
          response = requests.get(url, timeout=2)
        except requests.exceptions.Timeout:
          response.status_code = -1
        if response.status_code == 200:
          img = Image.open(BytesIO(response.content))
          img.save(img_name)
          print(f"Image {img_name} saved!")
          url_fail = False
        else:
          print(f"URL {url} failed?!? {response.status_code}")
    else:
      print(f"Image {img_name} already exists!")
      url_fail = False

    last_url = url

    r[1] = img_name

    if not url_fail:
      new_ds += ",".join(r) + "\n"

  with open(join(newcsvfilename),"w") as f:
    f.write(new_ds)


def splitdataset(csvfilename, train_val_test_ratios=[0.8,0.1,0.1], seed=42):
  """Read and split a dataset (TFLite Model Maker format) according
  to the ratios
  https://cloud.google.com/vision/automl/object-detection/docs/csv-format
  """
  with open(csvfilename,"r") as file:
    ds = file.read()
  
  last_img = ""
  img_idx = 0
  for l in ds.splitlines():
    r = l.split(',')
    if last_img != r[1]:
      last_img = r[1]
      img_idx += 1

  split_ratios = [round(img_idx*i) for i in train_val_test_ratios]
  shuffled = np.arange(img_idx)
  rnd = np.random.RandomState(seed)
  rnd.shuffle(shuffled)

  train = shuffled[:split_ratios[0]]
  val = shuffled[split_ratios[0]:split_ratios[0]+split_ratios[1]]
  test = shuffled[split_ratios[0]+split_ratios[1]:]

  new_ds = ""
  last_img = ""
  set_type = ""
  img_idx = 0
  for l in ds.splitlines():
    r = l.split(',')
    if last_img != r[1]:
      if img_idx in train:
        set_type = "TRAIN"
      elif img_idx in val:
        set_type = "VALIDATION"
      elif img_idx in test:
        set_type = "TEST"
      else:
        set_type = "WTF"
      last_img = r[1]
      img_idx += 1
    r[0] = set_type
    new_ds += ",".join(r) + "\n"

  with open(join(csvfilename),"w") as f:
    f.write(new_ds)

    
def drawbox(img, box):
  draw = ImageDraw.Draw(img)
  draw.rectangle([int(box[0]*img.size[0]),
                  int(box[1]*img.size[1]),
                  int(box[2]*img.size[0]),
                  int(box[3]*img.size[1])])
  return img

def flip(img, box):
  [x_min, y_min, x_max, y_max] = box
  img = ImageOps.flip(img)
  return img, [x_min, min([1-y_min,1-y_max]), x_max, max([1-y_min,1-y_max])]

def mirror(img, box):
  [x_min, y_min, x_max, y_max] = box
  img = ImageOps.mirror(img)
  return img, [min([1-x_min,1-x_max]), y_min, max([1-x_min,1-x_max]), y_max]

def flip_mirror(img, box):
  img, box = flip(img, box)
  img, box = mirror(img, box)
  return img, box

def rnd_solarize(img, seed=42):
  rnd = np.random.RandomState(seed)
  return ImageOps.solarize(img, threshold=rnd.randint(0,200,1))

def rnd_brightness(img, seed=42):
  rnd = np.random.RandomState(seed)
  enhancer = ImageEnhance.Brightness(img)
  return enhancer.enhance(rnd.rand())

def rnd_translate(img, box, seed=42):
  [x_min, y_min, x_max, y_max] = box
  rnd = np.random.RandomState(seed)
  x = rnd.randint(-min([x_min,x_max])*img.size[0],img.size[0]-max([x_min,x_max])*img.size[0],1)[0]
  y = rnd.randint(-min([y_min,y_max])*img.size[1],img.size[1]-max([y_min,y_max])*img.size[1],1)[0]
  img = img.transform(img.size, Image.AFFINE, (1, 0, -x, 0, 1, -y))
  x_min, y_min, x_max, y_max = x_min+x/img.size[0], y_min+y/img.size[1], x_max+x/img.size[0], y_max+y/img.size[1]
  return img, [x_min, y_min, x_max, y_max]


def augment_dataset(csvfilename, increaseby=3, seed=42):
  """Augment a dataset based on CSV format used by 
  TFLite Model Maker Object Detector
  https://cloud.google.com/vision/automl/object-detection/docs/csv-format
  """

  def augment(img, box, filename, extension, basename, ds_augmented, seed, increaseby):
    [x_min, y_min, x_max, y_max] = box
    for i in range(increaseby):
      filename_aug = filename + f"_{basename}_sol_{i}_" + "." + extension
      rnd_solarize(img.copy(), seed).save(filename_aug)
      ds_augmented += f"{r[0]},{filename_aug},{r[2]},{x_min:0.2f},{y_min:0.2f},,,{x_max:0.2f},{y_max:0.2f},,\n"
      
      filename_aug = filename + f"_{basename}_bright_{i}_" + "." + extension
      rnd_brightness(img.copy(), seed).save(filename_aug)
      ds_augmented += f"{r[0]},{filename_aug},{r[2]},{x_min:0.2f},{y_min:0.2f},,,{x_max:0.2f},{y_max:0.2f},,\n"

  with open(csvfilename,"r") as file:
    ds = file.read()

  ds_augmented = ""
  for i,l in enumerate(ds.splitlines()):
    print(f"Augmenting annotation {i+1}...")
    r = l.split(',')

    extension = r[1].split(".")[-1]
    filename = r[1][:-(len(extension)+1)]
    img_orig = Image.open(r[1])
    box = [float(fi) for fi in [r[3], r[4], r[7], r[8]]]

    img, [x_min, y_min, x_max, y_max] = flip(img_orig.copy(), box)
    filename_aug = filename + "_flip_" + "." + extension
    img.save(filename_aug)
    ds_augmented += f"{r[0]},{filename_aug},{r[2]},{x_min:0.2f},{y_min:0.2f},,,{x_max:0.2f},{y_max:0.2f},,\n"
    augment(img, [x_min, y_min, x_max, y_max], filename, extension, "flip", ds_augmented, seed+i, increaseby)

    img, [x_min, y_min, x_max, y_max] = mirror(img_orig.copy(), box)
    filename_aug = filename + "_mirror_" + "." + extension
    img.save(filename_aug)
    ds_augmented += f"{r[0]},{filename_aug},{r[2]},{x_min:0.2f},{y_min:0.2f},,,{x_max:0.2f},{y_max:0.2f},,\n"
    augment(img, [x_min, y_min, x_max, y_max], filename, extension, "mirror", ds_augmented, seed+i, increaseby)

    img, [x_min, y_min, x_max, y_max] = flip_mirror(img_orig.copy(), box)
    filename_aug = filename + "_flip-mirror_" + "." + extension
    img.save(filename_aug)
    ds_augmented += f"{r[0]},{filename_aug},{r[2]},{x_min:0.2f},{y_min:0.2f},,,{x_max:0.2f},{y_max:0.2f},,\n"
    augment(img, [x_min, y_min, x_max, y_max], filename, extension, "flip-mirror", ds_augmented, seed+i, increaseby)

    for ri in range(increaseby):
      img, [x_min, y_min, x_max, y_max] = rnd_translate(img_orig.copy(), box, seed+i)
      filename_aug = filename + f"_rnd_trans_{ri}_" + "." + extension
      img.save(filename_aug)
      ds_augmented += f"{r[0]},{filename_aug},{r[2]},{x_min:0.2f},{y_min:0.2f},,,{x_max:0.2f},{y_max:0.2f},,\n"
      augment(img, [x_min, y_min, x_max, y_max], filename, extension, f"rnd_trans_{ri}", ds_augmented, seed+i, increaseby)

  with open(csvfilename,"w") as file:
    file.write(ds+ds_augmented)
