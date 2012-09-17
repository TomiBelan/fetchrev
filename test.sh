#!/bin/bash

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


set -e

info () {
  echo $'\e[1m'"$*"$'\e[0m'
}

die () {
  echo "ERROR: $*"
  exit 1
}

exists () {
  git cat-file -t "$1" >/dev/null 2>&1
}

repo () {
  name=$1
  shift
  info "*** preparing repo $name"
  mkdir "$name"
  cd "$name"
  git init
  "$@"
  cd -
}

rm -rf testmain testa testb testx testy

info "***** TESTING FETCHREV *****"

repo testmain ../maketest.py 9 5
repo testa git fetch ../testmain r5c8:r5c8 r5c4:r5c4
repo testb git fetch ../testmain r5c2:r5c2 r5c3:r5c3

cd testmain
r5c2=`git rev-parse r5c2`
r5c3=`git rev-parse r5c3`
r5c4=`git rev-parse r5c4`
r5c8=`git rev-parse r5c8`
cd ..

cd testa
../fetchrev.py bash -c ../testb -- get r5c2
../fetchrev.py bash -c ../testb -- put r5c8
exists $r5c2 || die "didn't get r5c2"
exists $r5c3 && die "shouldn't have gotten r5c3"
cd ..
cd testb
exists $r5c8 || die "didn't put r5c8"
exists $r5c4 && die "shouldn't have put r5c4"
cd ..
info "PASS: transfer exactly what revs are asked for"
rm -rf testa testb testmain

info
info "***** TESTING THIN PACKS *****"

# now let's test whether thin packs work.
# http://stackoverflow.com/questions/1583904/what-are-gits-thin-packs
# thin packs only work if the filename is the same. they optimize the case
# when a big file changes, not when a new file is created which is similar to
# another big file that might be anywhere else in the repository. that would
# be too slow to check. the new blob must be on the same path.

repo testx true
repo testy true
cd testx
seq 1000000 > data
git add data
git commit -m seq
../fetchrev.py bash -c ../testy -- put HEAD
echo foo >> data
git add data
git commit -m foo
../fetchrev.py bash -c ../testy -- put HEAD 2>&1 | tee log
grep -q MiB log && die "a one-line patch needed more than 1 MiB of bandwidth"
info "PASS: a one-line patch was deltaified in a thin pack"
cp data data2
git add data2
git commit -m data2
../fetchrev.py bash -c ../testy -- put HEAD 2>&1 | tee log
grep -q MiB log && die "duplicating a file required retransfer of blob"
info "PASS: duplicating a file doesn't require retransfer of blob"
cp data data3
echo bar >> data3
git add data3
git commit -m data3
../fetchrev.py bash -c ../testy -- put HEAD 2>&1 | tee log
if grep -q MiB log; then
  info "BONUS FAILED: data3 could have been deltaified but wasn't"   # expected
else
  info "BONUS PASSED: data3 was deltaified (how is that possible?)"
fi
cd ..
rm -rf testx testy

info
info "***** TESTING SYNCGIT *****"

for rootorder in 'testa testb' 'testb testa'; do
  info "* testing with order of roots: $rootorder"
  rm -rf testmain testa testb
  mkdir testa testb
  repo testmain ../maketest.py 9 5
  repo testa/ra git fetch ../../testmain r5c8:r5c8
  repo testb/rb git fetch ../../testmain r5c2:r5c2

  cd testmain
  r5c2=`git rev-parse r5c2`
  r5c3=`git rev-parse r5c3`
  r5c4=`git rev-parse r5c4`
  r5c8=`git rev-parse r5c8`
  cd ..

  info "* simulating first sync"
  rsync -a testa/ testb/ --exclude='objects/*'
  rsync -a testb/ testa/ --exclude='objects/*'
  ./syncgit.py bash -c $rootorder

  cd testa/rb
  exists r5c2 || die "didn't get r5c2"
  cd ../..
  cd testb/ra
  exists r5c8 || die "didn't get r5c8"
  cd ../..

  info "* adding references using tags and reflogs"
  cd testa/ra
  ../../fetchrev.py bash -c ../../testmain -- get r5c4
  git tag tr5c4 $r5c4
  cd ../..
  cd testb/rb
  ../../fetchrev.py bash -c ../../testmain -- get r5c3
  git checkout -q $r5c3
  git checkout -q r5c2
  cd ../..

  info "* simulating second sync"
  rsync -a testa/ testb/ --exclude='objects/*'
  rsync -a testb/ testa/ --exclude='objects/*'
  ./syncgit.py bash -c $rootorder

  cd testa/rb
  exists $r5c3 || die "didn't get r5c3"
  cd ../..
  cd testb/ra
  exists tr5c4 || die "didn't get r5c4"
  cd ../..

  info "* changing one repo on both ends"
  cd testa/ra
  git fetch ../../testmain r5c6:r5c6
  cd ../..
  cd testb/ra
  git fetch ../../testmain r5c7:r5c7
  cd ../..

  info "* simulating third sync"
  rsync -a testa/ testb/ --exclude='objects/*'
  rsync -a testb/ testa/ --exclude='objects/*'
  ./syncgit.py bash -c $rootorder

  cd testa/ra
  exists r5c7 || die "didn't get r5c7"
  cd ../..
  cd testb/ra
  exists r5c6 || die "didn't get r5c6"
  cd ../..

  info "PASS: all synchronizations with order '$rootorder' successful."
  rm -rf testa testb testmain
done

info
info "All tests PASS."
