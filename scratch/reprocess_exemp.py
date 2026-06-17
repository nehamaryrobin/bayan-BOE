import sys
import os

sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from db.connection import get_connection
from scripts.pipeline import process_file

dec_no = "1484523"
pdf_filename = "2670362207exemp.pdf"

conn = get_connection()
cursor = conn.cursor()

print("Deleting existing DB entries for dec_no =", dec_no)
# Note: Foreign key constraint has ON DELETE CASCADE on fk_line_items_header, 
# so deleting from boe_header will automatically delete from boe_line_items.
cursor.execute("DELETE FROM boe_header WHERE dec_no = %s AND pdf_filename = %s", (dec_no, pdf_filename))
conn.commit()
cursor.close()
conn.close()

print("Re-running pipeline for data/processed/2670362207exemp.pdf")
success = process_file("data/processed/2670362207exemp.pdf")
print("Pipeline run success:", success)

# Now check DB to see if exemption_code_42 is inserted correctly.
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT item_no, exemption_code_42 FROM boe_line_items WHERE dec_no = %s ORDER BY item_no", (dec_no,))
rows = cursor.fetchall()
print("\nResults from DB:")
for r in rows:
    print(f"  Item {r[0]}: exemption_code_42 = {repr(r[1])}")
cursor.close()
conn.close()
