import re

input_path = r"d:\2026-15MAY\ML-project\frontend\src\components\Topbar.tsx.tmp"
output_path = r"d:\2026-15MAY\ML-project\frontend\src\components\Topbar.tsx"

with open(input_path, 'rb') as f:
    raw_data = f.read()

# Strip any NUL bytes which make tools think the file is binary
raw_data = raw_data.replace(b'\x00', b'')

text = raw_data.decode('utf-8', errors='replace')

# Clean box drawing and strange characters
text = re.sub(r'[\u2500-\u257F]+', '-', text)
text = text.replace('⌘', 'Ctrl')
text = text.replace('·', '.')
text = text.replace('…', '...')

# Replace Eimport with import
text = text.replace("// Topbar Component - Enterprise Eimport {", "import {")
text = text.replace("// Topbar Component - Enterprise Eimport", "import")
text = text.replace("Enterprise Eimport", "import")

# Let's insert newlines at key JavaScript constructs to make it readable
# We'll split the single line into a list of strings
# Let's do some simple replacements:
formatted = text
formatted = formatted.replace("import {", "\nimport {")
formatted = formatted.replace("export function Topbar() {", "\nexport function Topbar() {\n")
formatted = formatted.replace("const {", "\n  const {")
formatted = formatted.replace("const unreadCount =", "\n  const unreadCount =")
formatted = formatted.replace("const pendingCount =", "\n  const pendingCount =")
formatted = formatted.replace("const [time", "\n  const [time")
formatted = formatted.replace("const [isNotificationOpen", "\n  const [isNotificationOpen")
formatted = formatted.replace("const [isSettingsOpen", "\n  const [isSettingsOpen")
formatted = formatted.replace("const [isUserOpen", "\n  const [isUserOpen")
formatted = formatted.replace("const [isHelpOpen", "\n  const [isHelpOpen")
formatted = formatted.replace("const [skuSetting", "\n  const [skuSetting")
formatted = formatted.replace("const [budgetSetting", "\n  const [budgetSetting")
formatted = formatted.replace("const [pollIntervalSetting", "\n  const [pollIntervalSetting")
formatted = formatted.replace("useEffect(() => {", "\n  useEffect(() => {")
formatted = formatted.replace("const handleSaveSettings", "\n  const handleSaveSettings")
formatted = formatted.replace("const handleMarkAllRead", "\n  const handleMarkAllRead")
formatted = formatted.replace("const closeAll =", "\n  const closeAll =")
formatted = formatted.replace("const notifByType =", "\n  const notifByType =")

# Write output file
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(formatted)

print("Topbar.tsx written without NUL bytes, size:", len(formatted))
