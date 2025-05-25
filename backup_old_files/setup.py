from setuptools import setup, find_packages

setup(
    name="daria_interview_tool",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
    ],
) 