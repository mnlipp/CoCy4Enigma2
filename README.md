CoCy4Enigma2
============

Since I had my Dreambox, I have been looking for a UPnP renderer.
End of 2012 an implementation seemed to appear, but it wouldn't
run on my DM7025 -- probably too old.

So I finished my own implementation of a UPnP renderer after all
and the initial release did work on the DM7025.

Sorry to say, however, for all owners of a DM7025, I have moved 
to a VU Ultimo with OpenPLI by now and I will not maintain 
backward compatibility.

You should be able to install the renderer by downloading the 
latest version from the 
[releases](https://github.com/mnlipp/CoCy4Enigma2/releases) page, 
copy it to your Dreambox and run "opkg install <absolut file name>".

I have tried to list all dependencies in the package, so they
should install automatically. As, however, I have been experimenting
quite some time, my box is no longer "clean". If you experience any
problems, please report them by creating an
[issue](https://github.com/mnlipp/CoCy4Enigma2/issues).

Reporting errors
----------------

I have found that there are a lot of buggy control point implementations around. 
Therefore, if you experience a problem, first try to reproduce it using the 
[Fritz!App Media](https://play.google.com/store/apps/details?id=de.avm.android.fritzappmedia).
If things work when using this app, then your problem is most likely caused by 
your control point implementation.

Another thing that I've found out is that it is futile to attempt to help 
people who don't use OpenPLi (like I do). When I started this, I thought 
that with respect to the E2 API used by CoCy all E2 systems are the same, 
but this didn't prove to be true.

So, sorry, but unless you can reproduce a bug with the control point and E2 
system mentioned above or something that shows in the logs, I won't be able to 
help your.
