from bs4 import BeautifulSoup
def extract_product_details(html):
    soup = BeautifulSoup(html, "lxml")
    details = {"brand": None, "category": None}
    def get_value_for_label(label_text):
        el = soup.find(string=lambda t: t and label_text in t)
        if not el: return None
        parent = el.parent
        text = parent.get_text(strip=True)
        val = text.replace(label_text, "").strip()
        if val: return val
        grandparent = parent.parent
        if grandparent:
            text = grandparent.get_text(strip=True)
            val = text.replace(label_text, "").strip()
            if val: return val
        if parent.name == "td":
            next_td = parent.find_next_sibling("td")
            if next_td: return next_td.get_text(strip=True)
        return None
    details["category"] = get_value_for_label("Category:")
    details["brand"] = get_value_for_label("Brand:")
    for k, v in details.items():
        if v == "": details[k] = None
    return details

print(f"Test 1 (<p><b>Brand:</b> Polo</p>): {extract_product_details('<p><b>Brand:</b> Polo</p>')}")
print(f"Test 2 (<p>Brand: Polo</p>): {extract_product_details('<p>Brand: Polo</p>')}")
print(f"Test 3 (<td>Brand:</td><td>Polo</td>): {extract_product_details('<table><tr><td>Brand:</td><td>Polo</td></tr></table>')}")
