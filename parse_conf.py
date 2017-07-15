from ConfigParser import ConfigParser


def parse_conf(file_name):
    cp = ConfigParser()
    cp.read(file_name)
    sections = cp.sections()
    conf_dict = []
    for section in sections:
        s_dict = dict(cp.items(section))
        s_dict['name'] = section
        conf_dict.append(s_dict)

    return conf_dict


def main():
    config = parse_conf('test.conf')
    for app in config:
        print app['name']
        print app['describe']


if __name__ == '__main__':
    main()
