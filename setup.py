from setuptools import setup

setup(name='QuikPy',
      version='2025.11.1',
      author='Чечет Игорь Александрович',
      description='Библиотека-обертка, которая позволяет получить доступ к функционалу торгового теримнала QUIK из Python',
      url='https://github.com/cia76/QuikPy',
      packages=['QuikPy'],
      install_requires=[
            'pytz',  # ВременнЫе зоны
      ],
      python_requires='>=3.12',
      )
