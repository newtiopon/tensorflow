# Copyright 2018 The TensorFlow Authors. All Rights Reserved.
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
# ==============================================================================
"""Benchmark for the experimental `MatchingFilesDataset`."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import shutil
import tempfile
import time

import numpy as np

from tensorflow.python.client import session
from tensorflow.python.data.experimental.ops import matching_files
from tensorflow.python.data.ops import dataset_ops
from tensorflow.python.framework import errors
from tensorflow.python.framework import ops
from tensorflow.python.platform import test


class MatchingFilesBenchmark(test.Benchmark):
  """Benchmark for the experimental `MatchingFilesDataset`."""

  def benchmarkNestedDirectories(self):
    tmp_dir = tempfile.mkdtemp()
    width = 500
    depth = 10
    for i in range(width):
      for j in range(depth):
        new_base = os.path.join(tmp_dir, str(i),
                                *[str(dir_name) for dir_name in range(j)])
        os.makedirs(new_base)
        child_files = ['a.py', 'b.pyc'] if j < depth - 1 else ['c.txt', 'd.log']
        for f in child_files:
          filename = os.path.join(new_base, f)
          open(filename, 'w').close()

    patterns = [
        os.path.join(tmp_dir, os.path.join(*['**'
                                             for _ in range(depth)]), suffix)
        for suffix in ['*.txt', '*.log']
    ]

    deltas = []
    iters = 3
    for _ in range(iters):
      with ops.Graph().as_default():
        dataset = matching_files.MatchingFilesDataset(patterns)
        next_element = dataset_ops.make_one_shot_iterator(dataset).get_next()

        with session.Session() as sess:
          sub_deltas = []
          while True:
            try:
              start = time.time()
              sess.run(next_element)
              end = time.time()
              sub_deltas.append(end - start)
            except errors.OutOfRangeError:
              break
          deltas.append(sub_deltas)

    median_deltas = np.median(deltas, axis=0)
    print('Nested directory size (width*depth): %d*%d Median wall time: '
          '%fs (read first filename), %fs (read second filename), avg %fs'
          ' (read %d more filenames)' %
          (width, depth, median_deltas[0], median_deltas[1],
           np.average(median_deltas[2:]), len(median_deltas) - 2))
    self.report_benchmark(
        iters=iters,
        wall_time=np.sum(median_deltas),
        extras={
            'read first file:':
                median_deltas[0],
            'read second file:':
                median_deltas[1],
            'avg time for reading %d more filenames:' %
            (len(median_deltas) - 2):
                np.average(median_deltas[2:])
        },
        name='dataset_nested_directory(%d*%d)' %
        (width, depth))

    shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
  test.main()
