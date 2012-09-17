#!/usr/bin/env python2

# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import re
try:
    import cPickle as pickle
except:
    import pickle
import subprocess as SP
from collections import deque

import fetchrev
log = fetchrev.log


def list_files(base):
    yield base
    if os.path.isdir(base):
        for item in os.listdir(base):
            for entry in list_files(base + '/' + item):
                yield entry


def discover_repos():
    return [entry for entry in list_files('.')
        if os.path.isdir(entry) and entry.endswith('.git')]


def list_reachable_revs():
    result = set()
    hash_re = re.compile(r'^[a-fA-F0-9]{40}$')
    def read_file(filename):
        with open(filename) as f:
            return f.read()
    def process(content, hash_columns=1):
        for line in content.split('\n'):
            for word in line.split(' ')[0:hash_columns]:
                if hash_re.match(word):
                    result.add(word.lower())
                if word[0:1] == '^' and hash_re.match(word[1:]):
                    # packed-refs peeled tag
                    result.add(word[1:].lower())

    # process refs/
    for entry in list_files('refs'):
        if os.path.isfile(entry):
            process(read_file(entry))

    # process logs/
    for entry in list_files('logs'):
        if os.path.isfile(entry):
            process(read_file(entry), hash_columns=2)

    # process packed-refs and all refs directly under git dir (*_HEAD etc.)
    for entry in os.listdir('.'):
        if os.path.isfile(entry):
            process(read_file(entry))

    # other special-purpose state, such as in-progress rebase or am, isn't
    # processed -- it'd be a mess to do correctly and it's not really needed.
    return result - set(['0'*40])


def filter_existing_revs(revs):
    batch_checker = SP.Popen(['git', 'cat-file', '--batch-check'],
                             stdin=SP.PIPE, stdout=SP.PIPE)
    existing_revs = []
    for hash in revs:
        batch_checker.stdin.write(hash + '^{}\n')
        result = batch_checker.stdout.readline()
        if not result.endswith('missing\n'):
            existing_revs.append(hash)
    batch_checker.stdin.close()
    batch_checker.wait()
    return existing_revs


def local(input, output, args):
    local_root, remote_root = args
    pickle.dump(remote_root, output)
    os.chdir(local_root)
    local_root = os.getcwd()
    local_repos = set(discover_repos())
    remote_repos = set(pickle.load(input))

    for item in (local_repos - remote_repos):
        sys.stderr.write('WARNING: {} is only on local side\n'.format(item))
    for item in (remote_repos - local_repos):
        sys.stderr.write('WARNING: {} is only on remote side\n'.format(item))

    for repo in (local_repos & remote_repos):
        sys.stderr.write('------- local->remote {} --------\n'.format(repo))
        pickle.dump(repo, output)
        os.chdir(repo)
        revs = filter_existing_revs(list_reachable_revs())
        fetchrev.sender(input, output, revs, is_local=True)
        input.read(1)
        sys.stderr.write('------- remote->local {} --------\n'.format(repo))
        fetchrev.receiver(input, output)
        os.chdir(local_root)
    pickle.dump(None, output)


def remote(input=None, output=None):
    if not input: input = os.fdopen(0, 'r', 0)
    if not output: output = os.fdopen(1, 'w', 0)
    remote_root = pickle.load(input)
    os.chdir(remote_root)
    remote_root = os.getcwd()
    pickle.dump(discover_repos(), output)
    while True:
        repo = pickle.load(input)
        if not repo:
            break
        os.chdir(remote_root)
        os.chdir(repo)
        revs = filter_existing_revs(list_reachable_revs())
        fetchrev.receiver(input, output)
        output.write('F')
        fetchrev.sender(input, output, revs, is_local=False)


def connect(ssh_cmd, args):
    sys.path.insert(1, sys.path[0]+'/py-remoteexec')
    from remoteexec import remote_exec

    modules = [sys.path[0]+'/fetchrev.py', sys.path[0]+'/syncgit.py']
    p, s = remote_exec(ssh_cmd=ssh_cmd, module_filenames=modules,
                       main_func='syncgit.remote')
    local(s.makefile('r', 0), s.makefile('w', 0), args)
    p.wait()


def main():
    argv = sys.argv[1:]
    ssh_cmd = argv[0:argv.index('--')]
    program_args = argv[argv.index('--')+1:]
    connect(ssh_cmd, program_args)


if __name__ == '__main__':
    main()

