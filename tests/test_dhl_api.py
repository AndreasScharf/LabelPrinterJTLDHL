from dhl_api import struct_address

name, addiditional_name, street, street2, postalcode, city, country = struct_address(
    """frapp GmbH
Bachstraße 24-26
96188 Stettfeld
Deutschland
""")
print(name, addiditional_name, street, street2, postalcode, city, country)

assert name == 'frapp GmbH'
assert addiditional_name == ''
assert street == 'Bachstraße 24-26'
assert postalcode == '96188'
assert city == 'Stettfeld'
assert country == 'Deutschland'


name, addiditional_name, street, street2, postalcode, city, contry = struct_address(
    """Andreas Scharf
frapp GmbH
Bachstraße 24-26
96188 Stettfeld
Deutschland
""")
assert name == 'Andreas Scharf'
assert addiditional_name == 'frapp GmbH'
assert street == 'Bachstraße 24-26'
assert postalcode == '96188'
assert city == 'Stettfeld'
assert country == 'Deutschland'

name, addiditional_name, street, street2, postalcode, city, contry = struct_address(
    """Andreas Scharf
frapp GmbH
Bachstraße 24-26
Postfach 20
96188 Stettfeld
Deutschland
""")

assert name == 'Andreas Scharf'
assert addiditional_name == 'frapp GmbH'
assert street == 'Bachstraße 24-26'
assert street2 == 'Postfach 20'
assert postalcode == '96188'
assert city == 'Stettfeld'
assert country == 'Deutschland'