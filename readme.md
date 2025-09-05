# JTL Shipment Label
This software should optimize the buying and label printing of the labels of online packages

## Introduction
This label printer is used for the "A6 Versandetiketten, 105 x 148 mm" x4 labels, it optimizes label printing, DHL postmark purchasing, and printing.


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
