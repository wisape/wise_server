import os, psutil
import subprocess
from prettytable import PrettyTable
import collections


class WiseTask(object):
    def __init__(self, task_info):
        self._name = self.__set_task_info(task_info, 'name')
        self._describe = self.__set_task_info(task_info, 'describe')
        self._cmd = self.__set_task_info(task_info, 'command')
        self._args = self.__set_task_info(task_info, 'args')

        self.process = None

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type

    def __set_task_info(self, info, key):
        val = info.get(key)
        if val is None:
            if key == 'args':
                return []
            return ''
        if key == 'command' or key == 'args':
            return val.split()
        return val

    def __is_running(self):
        if self.process is None:
            return False
        ret = self.process.poll()
        if ret is None:
            return True
        else:
            return False

    def start(self):
        if self.__is_running():
            return None
        self.process = subprocess.Popen(self._cmd + self._args, shell=False)

    def stop(self):
        if self.__is_running():
            p = psutil.Process(self.process.pid)
            child = p.children()
            for c in child:
                c.kill()

            self.process.kill()
            self.process.wait()

    def restart(self):
        self.stop()
        self.start()

    def update(self, task_info):
        self._describe = self.__set_task_info(task_info, 'describe')
        if self._cmd != self.__set_task_info(task_info, 'command') or \
                self._args != self.__set_task_info(task_info, 'args'):
            self._cmd = self.__set_task_info(task_info, 'command')
            self._args = self.__set_task_info(task_info, 'args')
            if (self.__is_running()):
                self.restart()

    def status(self):
        status = collections.OrderedDict()
        status['name'] = self._name
        status['describe'] = self._describe
        status['state'] = self.__is_running() and 'Running' or 'Stoped'
        cmd_str = ' '.join(self._cmd + self._args)
        if len(cmd_str) > 40:
            cmd_str = cmd_str[:24] + '...' + cmd_str[-14:]
        status['command'] = cmd_str

        return status


def main():
    task_a = WiseTask(
        {'name': 'abc', 'describe': 'abc project', 'command': 'cat'})

    print task_a.name
    print task_a.type
    task_a.start()
    a = task_a.status()
    t = PrettyTable(a.keys())
    t.add_row(a.values())
    task_a.stop()
    b = task_a.status()
    t.add_row(b.values())

    print t


if __name__ == '__main__':
    main()
