import unittest

# test search parser

example_searches = [('genus where genus="Maxillaria,Encyclia"'), ('results'),
                    ('gen where genus="Maxillaria,Encyclia"'), ('results'),
                    ('gen where family_id.qualifier="test"'), ('results')]
                    