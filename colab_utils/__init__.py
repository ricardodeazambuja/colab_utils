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

from google.colab.output import eval_js
from PIL import Image
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
  elif imgformat == 'JPEG':
    str_data = "data:image/jpeg;base64," + imgBase64.decode(encoding="utf-8")
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
    draw.text((annotation[0]*w+2, annotation[1]*h+2), str(text), fill=color)
  
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
    Image.open(inputImg).save(imageBuffer, format=imgformat)
  elif type(inputImg) == np.ndarray:
    Image.fromarray(inputImg).save(imageBuffer, format=imgformat)
  elif "PIL" in str(type(inputImg)):
    inputImg.save(imageBuffer, format=imgformat)

  imgBase64 = b64encode(imageBuffer.getvalue())
  if imgformat == 'PNG':
    str_data = "data:image/png;base64," + imgBase64.decode(encoding="utf-8")
  elif imgformat == 'JPEG':
    str_data = "data:image/jpeg;base64," + imgBase64.decode(encoding="utf-8")
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