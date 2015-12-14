# -*- coding: utf-8 -*-
from copy import deepcopy
dict_vehicle = {
    "licence_plate" : "DF-118-FG",
    "model" : "BX",
    "model_year" : 1995,
    "engine" : "GO",
    "horse_power" : 2.0,
    "type_" : "sedan",
    "relais" : False,
    "constructor" : "Citroen",
    "horodateur" : "aa",
    "taximetre" : "aa",
    "date_dernier_ct" : "2015-03-03",
    "date_validite_ct" : "2016-03-03",
    "luxury" : False,
    "credit_card_accepted" : True,
    "nfc_cc_accepted" : False,
    "amex_accepted" : False,
    "bank_check_accepted" : False,
    "fresh_drink" : True,
    "dvd_player" : False,
    "tablet" : True,
    "wifi" : True,
    "baby_seat" : False,
    "bike_accepted" : False,
    "pet_accepted" : True,
    "air_con" : True,
    "electronic_toll" : False,
    "gps" : True,
    "cpam_conventionne" : False,
    "every_destination" : False,
    "color" : "grey",
    "special_need_vehicle" : True,
    "nb_seats": 4
}

dict_vehicle_2 = deepcopy(dict_vehicle)
dict_vehicle_2['licence_plate'] = 'second-licence'

dict_ads = {
    "category": "c1",
    "doublage": True,
    "insee": "75056",
    "numero": "1",
    "owner_name": "name",
    "owner_type": "company",
}
dict_ads_2 = deepcopy(dict_ads)
dict_ads_2['numero'] = "2"
dict_ads_2['insee'] = "34172"

dict_driver = {
    "last_name" : "last name",
    "first_name" : "first name",
    "birth_date" : "1980-03-03",
    "professional_licence" :  "ppkkpp",
    "departement" : {
        "numero" : "53"
        }
}
dict_driver_2 = deepcopy(dict_driver)
dict_driver_2['professional_licence'] = 'kkppkk'

dict_taxi = {
    "vehicle": {"licence_plate": "DF-118-FG"},
    "driver": {"professional_licence": "ppkkpp", "departement":"53"},
    "ads": {"insee": "75056", "numero": "1"},
    "status": "free"
}
dict_taxi_2 = {
        "vehicle": {"licence_plate": "second-licence"},
        "driver": {"professional_licence": "kkppkk", "departement": "53"},
        "ads": {"insee": "34172", "numero": "2"}
}
