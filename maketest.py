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


# Helper script for test.sh.

import os
import sys
import random
import subprocess as SP


basedata = os.urandom(1024*1024)


def write_object(type, content):
    p = SP.Popen(['git', 'hash-object', '-t', type, '-w', '--stdin'],
                 stdin=SP.PIPE, stdout=SP.PIPE)
    out, _ = p.communicate(content)
    if p.returncode != 0: raise OSError()
    return out.strip()


def update_ref(name, object):
    SP.check_call(['git', 'update-ref', name, object])


def make_commit(name, parents):
    blob = write_object('blob', basedata + name)
    tree = write_object('tree', '100644 d_' + name + '\0' + blob.decode('hex'))
    commit_data = 'tree ' + tree + '\n'
    for parent in parents:
        commit_data += 'parent ' + parent + '\n'
    commit_data += '\ncommit ' + name + '\n'
    commit = write_object('commit', commit_data)
    update_ref('refs/heads/' + name, commit)
    return commit


def construct(width, height):
    random.seed(width * height * (width+height))
    last = []
    for row in xrange(height):
        current = []
        for col in xrange(width):
            parents = random.sample(last, 2) if last else []
            commit = make_commit('r{}c{}'.format(row+1, col+1), parents)
            current.append(commit)
        last = current


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3:
        construct(int(sys.argv[1]), int(sys.argv[2]))
