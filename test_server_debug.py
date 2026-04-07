from glint.filters import list_filters

filters = list_filters()
print("filters =", repr(filters))

# Simulate what the server does
filters_js = str(filters).replace("'", "\\'")
print("filters_js =", filters_js[:100])

# Test the array iteration
print("Test iteration:")
for item in filters[:3]:
    print(f"  item: {item}, name: {item[0]}")
