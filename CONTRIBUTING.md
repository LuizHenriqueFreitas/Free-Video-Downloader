<!-- Last update 2026-31-07 -->
# To contributing with this software

If you want to contribut now, i'm aprecciated!   

At this moment i'm working to make the code really understandable, adding documentation comments and revising past decisions.   

#### Important thing: read Docs/ files, like: About.md, Vision.md and Vision.md to understand this project history and how it's built

Python packages are listed on `src/requirements.txt`:   
`pip install -r src/requirements.txt`

You also will need the external tools: ffmpeg + ffprobe, nodejs and yt-dlp (bundled on Windows at `src/tools/ffmpeg/bin/` and `src/bin/`, or installed on your system).

To run the unit tests, run pytest from the **repository root** (the tests import `src.` modules):   
`python -m pytest src/tests`


## If you don't agree with GET MEDIA FREE politices

So you can fork or clone this repo and made it in your way.     
There's just one thing:
- **This is a OPEN SOURCE application**
    - GET MEDIA FREE LINCENSE allow use this code to build another open source softwares.
    - ALSO, yt-dlp and FFmepg use the same type of license.
    - i.e. if you get this code to build a commercial application you run the risk of being sued
    by the mantainers of those other tools, in addition to Get Media Free.

### Documentation
Always explain what the code do, if you think is a obvoius, write that, and will be checked on code review, if was really obvius ok, if was not, you will be informed.   
Same happend if you documment beyond what is necessary, you will be notified to make this more objective and simple.


Tray to follow the used comment patterns