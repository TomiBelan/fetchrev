# Fetchrev (and syncgit) #

**Fetchrev** is an add-on command for [Git](http://git-scm.com/). It's like
an improved [git-fetch-pack](http://git-scm.com/docs/git-fetch-pack): it
connects to a remote Git repository and downloads some commits (plus all the
objects they depend on). But it can download any commits, not just refs
(branch tips). It requires shell access to the remote server.

**Syncgit** helps with synchronizing Git repositories using tools like
[rsync](http://en.wikipedia.org/wiki/Rsync) or
[Unison](http://www.cis.upenn.edu/~bcpierce/unison/). Normally, they only
transfer the parts of a file that have changed, but when Git repacks objects
into a new pack file with a different filename, they might not notice it's
almost the same thing as the old packfile.
To avoid resending everything, first synchronize
everything except `*.git/objects`, and then run syncgit. It will traverse
(the local and remote copy of) the synchronized directory tree, find Git
repositories, and use fetchrev to ensure all reachable objects are present on
both sides.

See the README for more info on dependencies and usage.