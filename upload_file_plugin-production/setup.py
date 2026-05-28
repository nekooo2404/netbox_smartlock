from setuptools import find_packages, setup

setup(
    name='upload_file_plugin',
    version='1.0.9',
    description='A NetBox plugin that provides a custom upload file plugin',
    author='Ngoc Anh',
    author_email='anhnoname91@gmail.com',
    url='https://gitlab.gtsc.vn/gtsc-dev/upload_file_plugin',
    packages=find_packages(include=["upload_file_plugin", "upload_file_plugin.*"]),
    include_package_data=True,
    install_requires=[],
    zip_safe=False,
    classifiers=[
        'Framework :: Django',
        'Programming Language :: Python :: 3',
    ],
)
