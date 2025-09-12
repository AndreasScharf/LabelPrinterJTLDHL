# JTL Shipment Label
This software should optimize the buying and label printing of the labels of online packages

## Introduction
This label printer is used for the "A6 Versandetiketten, 105 x 148 mm" x4 labels, it optimizes label printing, DHL postmark purchasing, and printing. With this application you can print up to 4 shipment labels at once.
<br>
e.g.<br>
https://www.amazon.de/Labelident-Laser-Etiketten-Adressaufkleber-Laserdrucker/dp/B0FBX2HYVQ?source=ps-sl-shoppingads-lpcontext&ref_=fplfs&smid=AA6SVWE0RX7N&th=1


## Setup
copy this .env file in your working dict and fill in your credentials
```
# JTL MSSQL Instance
DB_SERVER=
DB_DATABASE=
DB_USERNAME=
DB_PASSWORD=
DB_PORT=

SENDER_ADDR=

DHL_USERNAME=
DHL_PASSWORD=
DHL_CLIENT_ID=
DHL_CLIENT_SECRET=
```

## DHL API
For references this is the label post stamp purcasing
https://developer.dhl.com/api-reference/deutsche-post-internetmarke-post-paket-deutschland#get-started-section/


## DHL Postmarks handeling
All purchased postmarks will be stored in the `${PWD}/marks/` folder, the path will `./marks/md5({'receiver': 'receiver_address' -> string, 'product_id': 'product_id' -> string, 'date': 'YYYY-MM-DD' }).png`<br>

If you are using the same address on the same day the system will reuse the post mark you purchased already.


## JTL WAWI Integragion
The JTL WAWI Integration for getting the Shipment Addresses runs via MSSQL.
The SQL Query records the last onlineShop orders, which have no `tLieferschein` entry.

```
SELECT 
        a.cAuftragsNr,
        lfs.cLieferscheinNr,
        a.kKunde,
        a.kAuftrag,
        k.kInetKunde,
        a.dErstellt AS OrderDate,
        adr.cFirma AS 'Firma',
        adr.cAnrede AS 'Anrede',
        adr.cName AS CustomerLastName,
        adr.cVorname AS CustomerFirstName,
        adr.cStrasse AS Street,
        adr.cPLZ AS PLZ,
        adr.cOrt AS City,
        adr.cLand AS Country,
        adr.cAdressZusatz AS AddressAdditional
    FROM eazybusiness.Verkauf.tAuftrag a
    INNER JOIN tkunde k 
        ON a.kKunde = k.kKunde
    LEFT JOIN tAdresse adr 
        ON adr.kKunde = k.kKunde
        AND adr.nTyp = 0   -- Lieferadresse
    LEFT JOIN dbo.tLieferschein lfs 
        ON a.kAuftrag = lfs.kBestellung
    WHERE 
        {where_clause}
    ORDER BY a.dErstellt DESC;
```

## Legal Disclaimer
This project is provided as a free and open tool for anyone to use. It is developed with the sole purpose of helping users and does not generate any commercial benefit.

### No Affiliation
This project is provided as a free and open tool for anyone to use. It is developed with the sole purpose of helping users and does not generate any commercial benefit.

### No Warranty
This software is provided "as is" without any warranties or guarantees. The author is not responsible for any issues, data loss, or damages arising from its use.

By using this tool, you acknowledge and accept these terms.