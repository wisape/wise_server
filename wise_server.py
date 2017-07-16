import atexit
import os
import sys
import time
import signal
from wise_sched import WiseSched
from parse_conf import parse_conf


class WDaemon:
    ''' 
    pid_path:  pid file path
    stderr: error log flie path
    verbose: debug level,  0 close, 1 open, default 1
    '''

    def __init__(self, pid_path, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull, home_dir='.', umask=022, verbose=1):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pid_path
        self.home_dir = home_dir
        self.verbose = verbose
        self.umask = umask
        self.daemon_alive = True

    def daemonize(self):
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            sys.stderr.write('fork #1 failed: %d (%s)\n' %
                             (e.errno, e.strerror))
            sys.exit(1)

        os.chdir(self.home_dir)
        os.setsid()
        os.umask(self.umask)

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            sys.stderr.write('fork #2 failed: %d (%s)\n' %
                             (e.errno, e.strerror))
            sys.exit(1)

        sys.stdout.flush()
        sys.stderr.flush()

        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        if self.stderr:
            se = file(self.stderr, 'a+', 0)
        else:
            se = so

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        def sig_handler(signum, frame):
            self.daemon_alive = False
        signal.signal(signal.SIGTERM, sig_handler)
        signal.signal(signal.SIGINT, sig_handler)

        if self.verbose >= 1:
            print 'daemon process started ...'

        atexit.register(self.del_pid)
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write('%s\n' % pid)

    def get_pid(self):
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        except SystemExit:
            pid = None
        return pid

    def del_pid(self):
        if os.path.exists(self.pidfile):
            os.remove(self.pidfile)

    def start(self, *args, **kwargs):
        if self.verbose >= 1:
            print 'ready to starting ......'
        # check for a pid file to see if the daemon already runs
        pid = self.get_pid()
        if pid:
            msg = 'pid file %s already exists, is it already running?\n'
            sys.stderr.write(msg % self.pidfile)
            sys.exit(1)
        # start the daemon
        self.daemonize()
        self.run(*args, **kwargs)

    def stop(self):
        if self.verbose >= 1:
            print 'stopping ...'
        pid = self.get_pid()
        if not pid:
            msg = 'pid file [%s] does not exist. Not running?\n' % self.pidfile
            sys.stderr.write(msg)
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)
            return
        # try to kill the daemon process
        try:
            i = 0
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
                i = i + 1
                if i % 10 == 0:
                    os.kill(pid, signal.SIGHUP)
        except OSError, err:
            err = str(err)
            if err.find('No such process') > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)
            if self.verbose >= 1:
                print 'Stopped!'

    def restart(self, *args, **kwargs):
        self.stop()
        self.start(*args, **kwargs)

    def is_running(self):
        pid = self.get_pid()
        # print(pid)
        return pid and os.path.exists('/proc/%d' % pid)

    def run(self, *args, **kwargs):
        'NOTE: override the method in subclass'
        print 'base class run()'


class WiseServer(WDaemon):
    def __init__(self, conf_file):
        self.name = 'wise_server'
        pid_path = '/tmp/' + self.name + '.pid'
        log_path = '/tmp/' + self.name + '.log'
        err_path = '/tmp/' + self.name + '.err.log'
        WDaemon.__init__(self, pid_path=pid_path,
                         stdout=log_path, stderr=err_path)

        self.conf_file = conf_file

        self.scheduler = WiseSched()

        self.pipe_in_name = '/tmp/' + self.name + '.pipe.in'
        self.pipe_out_name = '/tmp/' + self.name + '.pipe.out'

        self.__set_pipe()

    def run(self, **kwargs):
        print "start task!!!"
        config = parse_conf(self.conf_file)
        for item in config:
            self.scheduler.add_task(item)

        self.scheduler.start()
        self.__parse_cmd()

    def __set_pipe(self):
        if not os.access(self.pipe_in_name, os.F_OK):
            os.mkfifo(self.pipe_in_name)
        if not os.access(self.pipe_out_name, os.F_OK):
            os.mkfifo(self.pipe_out_name)

    def __send_cmd(self, cmd, name=None, data=None):
        if name is None:
            name = self.name
        msg = {'name': name, 'cmd': cmd, 'data': str(data)}

        cmd_pipe = os.open(self.pipe_out_name, os.O_WRONLY)
        os.write(cmd_pipe, str(msg))
        os.close(cmd_pipe)
        ret_pipe = os.open(self.pipe_in_name, os.O_RDONLY)
        ret = os.read(ret_pipe, 1000)
        os.close(ret_pipe)
        return ret

    def __parse_cmd(self):
        while True:
            cmd_pipe = os.open(self.pipe_out_name, os.O_RDONLY)
            msg = os.read(cmd_pipe, 1000)
            os.close(cmd_pipe)

            msg = eval(msg)
            name = msg['name']
            cmd = msg['cmd']
            data = eval(msg['data'])
	    ret = 0

            if name == self.name:
                if cmd == 'status':
                    ret = self.scheduler.status()
                elif cmd == 'stop':
                    self.scheduler.stop()
                elif cmd == 'clear':
                    self.scheduler.clear_tasks()
                elif cmd == 'update':
                    config = parse_conf(self.conf_file)
                    for item in config:
                        self.scheduler.add_task(item)
                else:
                    pass
            else:
                if cmd == 'del_task':
                    self.scheduler.del_task(name)
                elif cmd == 'update_task':
                    self.scheduler.update_task(data)
                else:
                    pass
	    ret_pipe = os.open(self.pipe_in_name, os.O_WRONLY)
	    os.write(ret_pipe, str(ret))
	    os.close(ret_pipe)

    def stop(self):
        if self.is_running():
            self.__send_cmd('stop')
            WDaemon.stop(self)

    def update(self):
        self.__send_cmd('update')

    def del_task(self, name):
        self.__send_cmd(cmd='del_task', name=name)

    def update_task(self, task_info):
        self.__send_cmd(cmd='update_task', name=task_info['name'], data=task_info)

    def clear(self):
        self.__send_cmd('clear')

    def status(self):
        return self.__send_cmd('status')


if __name__ == '__main__':
    help_msg = 'Usage: python %s <start|stop|restart|status>' % sys.argv[0]
    if len(sys.argv) < 2:
        print help_msg
        sys.exit(1)
    ws = WiseServer('/etc/wise_server.conf')

    if sys.argv[1] == 'start':
        ws.start()
    elif sys.argv[1] == 'stop':
        ws.stop()
    elif sys.argv[1] == 'update':
        ws.update()

    elif sys.argv[1] == 'stop_task':
        ws.del_task(sys.argv[2])

    elif sys.argv[1] == 'restart':
        ws.restart()
    elif sys.argv[1] == 'status':
        alive = ws.is_running()
        if alive:
            print 'process [%s] is running...' % ws.get_pid()
            print ws.status()
        else:
            print 'daemon process [%s] stopped' % ws.name
    elif sys.argv[1] == 'deltask':
        ws.del_task(sys.argv[2])
    elif sys.argv[1] == 'updatetask':
        task_info = eval(sys.argv[2])
        if type(task_info) != dict:
            raise ValueError('param is not task info dict')
        ws.update_task(task_info)
    else:
        print 'invalid argument!'
        print help_msg
