from setuptools import setup


setup(
    name='ldaplog',
    version='1.0',
    url='https://github.com/eea/ldaplog',
    license='Mozilla Public License',
    author='Eau de Web',
    author_email='office@eaudeweb.ro',
    description='LDAP event monitor',
    packages=['ldaplog'],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=[
        'MySQL-python==1.2.3',
        'raven==2.0.12.2',
        'SQLAlchemy==0.7.9',
        'Flask==0.9',
        'Jinja2==2.6',
        'Werkzeug==0.8.3',
        'Flask-Script==0.5.3',
        'python-dateutil==2.1',
        'pytz==2012j',
        'six==1.2.0',
        'times==0.6.1',
        'Flask-Admin==1.0.6',
        'Flask-WTF==0.8.2',
        'WTForms==1.0.3',
        'python-ldap==2.4.10',
        'simplejson==3.0.7',
        'tornado==2.4.1',
    ],
    entry_points = {'console_scripts': ['manage = ldaplog.manage:main']},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
