# picoducky

> demo / working code incoming when I actually have hardware to run this on

Remote control server with Picoducky. What this means is you're able to remotely control your computer from somewhere else just by plugging this in, without any external permissions!

But it requires a bit of gymnastics to get there. The picoducky doesn't have wireless, but you can just use the computer's wireless connection to communicate with the server. But how to relay information from there? Well, it turns out you can advertise as a composite device: Namely a keyboard AND a usb serial at the same time. So you can just communicate code from there. You can essentially run arbitrary code on the computer because you could just type in terminal `curl | sh`. Screenshotting the whole screen usually requires elevated permissions too, but in this case, with keyboard access, you can just spam the screenshot hotkey.

## To test (for now)

> mac only for now

`git clone`, `cd` in, etc etc

```bash
uv sync
cd cc-src
uv run server.py
uv run listener.py # in another terminal window
```
Then press cmd + ctrl + shift + 3 to see the screenshot propogate
