
Fetchrev (and syncgit)
======================

**Fetchrev** is an add-on command for [Git](http://git-scm.com/). It's like
an improved [`git-fetch-pack`](http://git-scm.com/docs/git-fetch-pack): it
connects to a remote Git repository and downloads some commits (plus all the
objects they depend on). But it can download any commits, not just refs
(branch tips). It requires shell access to the remote server.

**Syncgit** helps with synchronizing Git repositories using tools like
[rsync](http://en.wikipedia.org/wiki/Rsync) or
[Unison](http://www.cis.upenn.edu/~bcpierce/unison/). Normally, they only
transfer the parts of a file that have changed, but when Git repacks objects
into a new pack file with a different filename, they might not notice it's
almost the same thing. To avoid resending everything, first synchronize
everything except `*.git/objects`, and then run syncgit. It will traverse
(the local and remote copy of) the synchronized directory tree, find Git
repositories, and use fetchrev to ensure all reachable objects are present on
both sides.

Fetchrev and syncgit depend on
[`py-remoteexec`](https://bitbucket.org/danderson/py-remoteexec) so that they
can run without having to install anything on the server (except for Git and
Python). Download it and place the `py-remoteexec` directory in this one (side
by side with `fetchrev.py` and this README).

Shallow repositories are not supported for now.

Usage
-----

Fetchrev usage:
`fetchrev.py <connection> -- <get/put> <remote-dir> <commits...>`

* `<connection>`: A ssh-like command that will connect to the remote side and
  execute its last argument as a shell command. (That last argument will be
  provided by fetchrev and `py-remoteexec`.) For example,
  `ssh -o SomeSSHOption user@host`. If you don't want to go over the network,
  just use `bash -c` (it also fits the definition of "something that
  executes its last argument").
* `<get/put>`: Either `get` to download objects or `put` to upload objects.
  Fetchrev can do both, even if its name only contains "fetch".
* `<remote-dir>`: Where's the remote Git repository.
* `<commits...>`: The commits to transmit. Will be parsed with `git-rev-parse`
  on the sender's side (so you can use the sender's refs if you want to, but
  plain hashes are also OK).

Syncgit usage:
`syncgit.py <connection> -- <local-root> <remote-root>`

* `<connection>`: Same as above.
* `<local-root>` and `<remote-root>`: Where to search for Git repositories to
  synchronize.

