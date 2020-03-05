#!/usr/bin/env python
# Copyright 2019 Cloudera Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Assert that a system has the correct libraries/binaries to build the
# native toolchain. Since we support centos5 which ships with python2.6,
# this script must be python2.6 .

import distutils.core  # noqa: F401
import distutils.spawn
import distutils.sysconfig
import platform
import subprocess
import logging
import os
import re
import shutil
import sys

LOG = logging.getLogger('assert-dependencies')


def check_output(cmd):
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  ret = p.communicate()
  if p.poll():
    raise Exception('%s returned' % cmd, p.returncode)
  out, err = ret
  out = out.decode('utf-8')
  err = err.decode('utf-8')
  return out, err


def regex_in_list(regex, l):
  cr = re.compile(regex)
  return any(map(cr.match, l))


def check_python_headers_present():
  # Causes thrift to fail silently, so ensure this is present
  include = os.path.join(distutils.sysconfig.get_python_inc(), 'Python.h')
  LOG.info('Checking if %s exists', include)
  assert os.path.isfile(include)


def check_libraries():
  patterns = [r'libdb.*\.so',
              r'libffi.*\.so',
              r'libkrb.*\.so',
              r'libncurses\.so',
              r'libsasl.*\.so',
              r'libcrypto\.so',
              r'libz\.so']
  libraries = [line.split()[0] for line in check_output(["ldconfig", "-p"])[0].splitlines()]
  for pattern in patterns:
    LOG.info('Checking pattern: %s' % pattern)
    if not regex_in_list(pattern, libraries):
      raise Exception('Unable to find pattern: %s in `ldconfig -p`' % pattern)


def check_path():
  progs = ['aclocal',
           'autoconf',
           'automake',
           'aws',
           'bison',
           'ccache',
           'flex',
           'lsb_release',
           'libtool',
           'gcc',
           'git',
           'java',
           'make',
           ('mawk', 'gawk'),
           'mvn',
           'patch',
           'pigz',
           ('python', 'python3'),
           'soelim',
           'unzip',
           'bzip2',
           'yacc']
  which = distutils.spawn.find_executable
  for p in progs:
    if isinstance(p, tuple):
      LOG.info('Checking for any program of: %s' % ', '.join(p))
      if not any(map(which, p)):
        raise Exception('Unable to find any of \'%s\' in PATH' % ', '.join(p))
      continue
    LOG.info('Checking program: %s' % p)
    if not which(p):
      raise Exception('Unable to find %s in PATH' % p)


def check_openssl_version():
  LOG.info('Checking openssl version')
  want = '1.0.1e'
  distro = platform.dist()[1]
  if distro == 'centos':
    out = check_output(['rpm', '-qa', 'openssl'])[0].rstrip()
    if want not in out:
      raise Exception('Unexpected openssl version. Was: %s, expected: %s' % (out, want))


def check_aws_works():
  # Due to the python/pip version discrepancies it's
  # worthwhile to verify that aws was correctly installed
  # and not just in our path
  LOG.info('Checking that aws is correctly isntalled.')
  check_output(['aws', '--version'])


def check_mvn_works():
  LOG.info('Checking that mvn is correctly installed.')
  check_output(['mvn', '--version'])


def check_ccache_works():
  # Older versions of ccache can cause build failures and weirdness (e.g. on Redhat 6)
  # Verify that the version we installed is present.
  want = '3.3.3'
  LOG.info('Checking that ccache is correctly installed.')
  out = check_output(['ccache', '--version'])[0]
  if want not in out:
    raise Exception('Unexpected ccache version. Was: %s, expected: %s' % (out, want))


def check_java_version():
  # Building Kudu requires Java 8.
  want = '1.8.0'
  LOG.info('Checking that java is correctly installed.')
  # java -version has multiline output, so combine it into a single string
  out = "".join(check_output(['java', '-version']))
  if want not in out:
    raise Exception('Unexpected java version. Was: %s, expected: %s' % (out, want))


def git_clone_works_with_https():
  distro, version, _ = platform.dist()
  if distro == 'centos' and version.startswith('6'):
    # See: https://github.com/apache/kudu.git/info/refs
    LOG.info('Checking if git can clone from https://github.com')
    check_output(['git', 'ls-remote', '--heads', 'https://github.com/apache/kudu'])


def main():
  logging.basicConfig(level=logging.INFO)
  check_libraries()
  git_clone_works_with_https()
  check_path()
  check_openssl_version()
  check_python_headers_present()
  check_aws_works()
  check_mvn_works()
  check_java_version()


if __name__ == '__main__':
  main()
