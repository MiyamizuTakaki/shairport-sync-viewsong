# shairport-sync-viewsong

## 这个代码可以让你通过连接树莓派的spi屏幕来看歌曲的专辑图片，歌曲名和歌手

### 先决条件

- 树莓派（如果是树莓派5，需要自备外置声卡）
  
- ST7735屏幕，如果不是，需要修改代码
  
- 安装shairport-sync
  
- 电脑（废话）
  

### 步骤

编辑`sudo nano /etc/shairport-sync.conf`

修改如下代码

`metadata ={
 enabled = "yes"; // set this to yes to get Shairport Sync to solicit metadata from the source and to pass it on via a pipe
 include_cover_art = "yes"; // set to "yes" to get Shairport Sync to solicit cover art from the source and pass it via the pipe. You must also set "enabled" to "yes".
 cover_art_cache_directory = "/tmp/shairport-sync/.cache/coverart"; // artwork will be stored in this directory if the dbus or MPRIS interfaces are enabled or if the MQTT client is in use. Set it t>
 pipe_name = "/tmp/shairport-sync-metadata";
// pipe_timeout = 5000; // wait for this number of milliseconds for a blocked pipe to unblock before giving up
// socket_address = "226.0.0.1"; // if set to a host name or IP address, UDP packets containing metadata will be sent to this address. May be a multicast address. "socket-port" must be non-zero and "e>
// socket_port = 5555; // if socket_address is set, the port to send UDP packets to
// socket_msglength = 65000; // the maximum packet size for any UDP metadata. This will be clipped to be between 500 or 65000. The default is 500.
};``

这一步就是打开pipe接口

安装以下依赖

`pip install adafruit-blinka adafruit-circuitpython-rgb-display inotify-simple
sudo apt install python3-pil`

克隆，fork这个代码，可以用了。

切换歌曲不要太快，会跟不上的，而且会引发白屏，大概就是线程抢占spi导致刷新会有问题
