# Copyright 2022 QHAna plugin runner contributors.
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

from qhana_plugin_registry.db.models.plugins import RAMP, PluginTag, TagToRAMP


def test_ramp_init_tags(tmp_db, *args):
    tags = [PluginTag("hello"), PluginTag("world")]
    for tag in tags:
        tmp_db.session.add(tag)
    tmp_db.session.flush()  # create IDs for tags
    for tag in tags:
        assert tag.id is not None
    ramp = RAMP("demo", "descr", tags=tags)
    tmp_db.session.add(ramp)
    tmp_db.session.commit()


def test_ramp_manual_init_tags(tmp_db, *args):
    tags = [PluginTag("hello"), PluginTag("world")]
    for tag in tags:
        tmp_db.session.add(tag)
    ramp = RAMP("demo", "descr")
    for tag in tags:
        tmp_db.session.add(TagToRAMP(ramp, tag))
    tmp_db.session.add(ramp)
    tmp_db.session.commit()
