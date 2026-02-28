# Please ignore for now
This is an ongoing project and is primarily created by the inbuilt AI agent
Further developments to come


# API Grid Viewer

This simple Python desktop app fetches data from a public API and displays the returned items in a grid with filtering support. It's built using `tkinter` and `requests`.

## Requirements

- Python 3.6+
- Install dependencies with:
  ```bash
  pip install -r requirements.txt
  ```

## Usage

1. Run the app:
   ```bash
   python main.py
   ```
2. Enter the API URL (pre-filled with a placeholder) and click **Fetch**.
3. The returned `items` list should contain objects with `name` and `value` fields. They will appear in the table.
4. Use the **Filter** box to type part of an item name; rows not matching will be removed from the view entirely.

### Secondary API calls

- You can supply a list of item slugs (one per line) by clicking **Load slugs** and selecting a text file.  This is useful for ad‑hoc files anywhere on disk.
- Pre‑packaged slug files may be placed in the workspace `slugs/` folder; a dropdown next to the button lets you pick one of them instead of browsing.  Selecting an entry simply reads it (no files are copied or moved).
- Once slugs are loaded the label shows the count; press **Fetch Orders** to query `orders/item/{slug}/top` for each slug.
- The table will switch to display order rows (slug, type, price, quantity) instead of the basic item list.
- Filtering still works against the first column (slug when viewing orders).

## Notes

- Adjust the JSON parsing logic in `main.py` if the API returns a different structure.
- The app stores the raw data and updates the grid on each fetch.
