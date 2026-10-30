from setuptools import setup, find_packages

setup(
    name='django-user-activity',
    version='0.0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'django',
        'django-solo>=2.5',
    ],
    author='Md. Rezaul Karim',
    author_email='rezaul.cse.pust17@gamil.com',
    license='MIT',
    description='A Django app for tracking user activity',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/rkpust/django-user-activity',
    classifiers=[
        'Framework :: Django',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent'
    ],
)
