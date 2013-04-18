import os
from fabric.api import *

_host, _directory = os.environ['DEPLOYMENT_TARGET'].split(':')
env['hosts'] = [_host]
env['target_directory'] = _directory
env['use_ssh_config'] = True


@task
def pack():
    # create a new source distribution as tarball
    local('python setup.py sdist --formats=gztar', capture=False)

@task
def restart():
    # create a new source distribution as tarball
    run('%s/bin/supervisorctl restart ldaplogger' % env['target_directory'])

@task
def deploy():
    execute("pack")
    # figure out the release name and version
    dist = local('python setup.py --fullname', capture=True).strip()
    # upload the source tarball to the temporary folder on the server
    put('dist/%s.tar.gz' % dist, '/tmp/%s.tar.gz' % dist)
    # create a place where we can unzip the tarball, then enter
    # that directory and unzip it
    run('mkdir /tmp/%s' % dist)
    try:
        with cd('/tmp/%s' % dist):
            run('tar xzf /tmp/%s.tar.gz' % dist)
            # now setup the package in our virtual environment
            with cd(dist):
                run('%s/bin/python setup.py install' % env['target_directory'])
    except:
        pass
    finally:
        run('rm -rf /tmp/%s /tmp/%s.tar.gz' % (dist, dist))
