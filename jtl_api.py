from MSSQLDatabase import MSSQLDatabase

def fetch_orders(db, days=90, lieferschein_exists=False, is_online_order=True):
    """
    Fetch orders from the database based on the given parameters.

    :param db: MSSQLDatabase instance
    :param days: Number of days to look back for orders
    :param lieferschein_exists: Whether a Lieferschein should exist
    :param is_online_order: Whether the order should be an online order
    :return: List of orders
    """

    # Build the WHERE clause dynamically
    conditions = []
    if is_online_order:
        conditions.append("a.kShopauftrag IS NOT NULL")
    if lieferschein_exists:
        conditions.append("lfs.kLieferschein IS NOT NULL")
    else:
        conditions.append("lfs.kLieferschein IS NULL")
    conditions.append("a.dErstellt >= DATEADD(DAY, -?, GETDATE())")
    where_clause = " AND ".join(conditions)

    # Define the SQL query
    query = f"""
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
    """

    # Execute the query
    try:
        results = db.fetch_results(query, [days])

        #print(results)
        return list(map(_format_address, results))
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def _format_address(addr: list[str]) -> str:
    """
    Map a raw 2D array row (company, title, last, first, street, postal, city, country)
    into a formatted address block.
    """
     # slice from column 6
    company, title, last, first, street, postal, city, country = addr[6:14]

    lines = []

    # company line (with newline after if non-empty)
    if company.strip():
        lines.append(company.strip())

    # person line (first + title + last, skipping empties, adding spaces between)
    name_parts = [first.strip(), title.strip(), last.strip()]
    name = " ".join([p for p in name_parts if p])
    if name:
        lines.append(name)

    # street
    if street.strip():
        lines.append(street.strip())

    # postal + city
    if postal.strip() or city.strip():
        lines.append(f"{postal.strip()} {city.strip()}".strip())

    # country
    if country.strip():
        lines.append(country.strip())

    return "\n".join(lines)

def main():
    with MSSQLDatabase.connect_with_env() as db:
        r = fetch_orders(db, 30)
        print(r)

if __name__ == '__main__':
    main()