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

log = sys.stderr.write
log = lambda msg: None   # comment this line to enable verbose mode


ASKED = 1
HAVE = 2
NEED = 3

def sender(input, output, revs, is_local, thin=True):
    revs_objects = SP.check_output(
        ['git', 'rev-parse'] + list(revs)).split()
    obj_re = re.compile(r'^[0-9a-fA-F]{40}$')
    for obj in revs_objects:
        if not obj_re.match(obj): raise ValueError()
    log('sender: sending ' + repr(revs_objects) + '\n')
    object_status = dict()
    query_queue = deque()
    def ask(obj):
        if obj in object_status: return
        query_queue.append(obj)
        object_status[obj] = ASKED
        log('sender: asking about ' + obj + '\n')
        output.write('Q' + obj)
    for obj in revs_objects:
        ask(obj)
    while query_queue:
        have_it = input.read(1) == 'Y'
        obj = query_queue.popleft()
        log('sender: received answer for {}: {}\n'.format(obj, have_it))
        object_status[obj] = HAVE if have_it else NEED
        if not have_it:
            parents = SP.check_output(['git', 'rev-parse', obj+'^@']).split()
            for parent in parents:
                ask(parent)
    log('sender: starting packing\n')
    output.write('T')
    args = ['git', 'pack-objects', '--progress', '--stdout']
    if is_local: args += ['--all-progress']
    packer_input = []
    if thin:
        args += ['--revs', '--thin']
        for obj, status in object_status.iteritems():
            if status == HAVE:
                packer_input.append('^' + obj + '\n')
        for obj in revs_objects:
            if object_status[obj] == NEED:
                packer_input.append(obj + '\n')
    else:
        # TODO: we need --revs even when thin is False, because object_status
        # only has commits and pack-objects wants the complete list of objects,
        # including trees and blobs. Can something be done about that?
        args += ['--revs']
        for obj, status in object_status.iteritems():
            if status == NEED:
                packer_input.append(obj + '\n')
    packer = SP.Popen(args, stdin=SP.PIPE, stdout=output)
    packer.communicate(''.join(packer_input))
    log('sender: finished\n')


def receiver(input, output):
    batch_checker = SP.Popen(['git', 'cat-file', '--batch-check'],
                             stdin=SP.PIPE, stdout=SP.PIPE)
    log('receiver: ready\n')
    while True:
        command = input.read(1)
        if command == 'Q':
            hash = input.read(40)
            log('receiver: asked about ' + hash + '\n')
            # use ^{} to suppress dumb "error: unable to find <hash>" message
            # which happens only when input is a plain hash.
            batch_checker.stdin.write(hash + '^{}\n')
            result = batch_checker.stdout.readline()
            output.write('N' if result.endswith('missing\n') else 'Y')
        elif command == 'T':
            break
        else:
            raise ValueError()
    batch_checker.stdin.close()
    batch_checker.wait()
    log('receiver: starting unpacking\n')
    unpacker = SP.Popen(['git', 'unpack-objects'], stdin=input, stdout=SP.PIPE)
    unpacker.wait()
    log('receiver: finished\n')


def local(input, output, args):
    remote_wd = args[1]
    pickle.dump(remote_wd, output)
    if args[0] == 'get':
        output.write('G')
        pickle.dump(args[2:], output)
        receiver(input, output)
    elif args[0] == 'put':
        output.write('P')
        sender(input, output, args[2:], True)
    else:
        raise ValueError()


def remote(input=None, output=None):
    if not input: input = os.fdopen(0, 'r', 0)
    if not output: output = os.fdopen(1, 'w', 0)
    remote_wd = pickle.load(input)
    os.chdir(remote_wd)
    mode = input.read(1)
    if mode == 'G':
        revs = pickle.load(input)
        log('remote: is sender, and local is receiver\n')
        sender(input, output, revs, False)
    elif mode == 'P':
        log('remote: is receiver, and local is sender\n')
        receiver(input, output)
    else:
        raise ValueError()


def connect(ssh_cmd, args):
    sys.path.insert(1, sys.path[0]+'/py-remoteexec')
    from remoteexec import remote_exec

    modules = [sys.path[0]+'/fetchrev.py']
    p, s = remote_exec(ssh_cmd=ssh_cmd, module_filenames=modules,
                       main_func='fetchrev.remote')
    local(s.makefile('r', 0), s.makefile('w', 0), args)
    p.wait()


def main():
    argv = sys.argv[1:]
    ssh_cmd = argv[0:argv.index('--')]
    program_args = argv[argv.index('--')+1:]
    connect(ssh_cmd, program_args)


if __name__ == '__main__':
    main()

