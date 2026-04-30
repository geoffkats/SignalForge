$path = "src\styles.css"
$css = Get-Content $path -Raw -Encoding UTF8

# Teal → Electric Indigo
$css = $css -replace 'rgba\(127, 236, 226,', 'rgba(99, 102, 241,'
$css = $css -replace 'rgba\(46, 232, 212,', 'rgba(79, 70, 229,'
$css = $css -replace '#7fece2', '#818cf8'
$css = $css -replace '#2ee8d4', '#6366f1'
$css = $css -replace '#00e5c4', '#6366f1'

# Amber → Coral/Orange
$css = $css -replace 'rgba\(240, 184, 94,', 'rgba(251, 146, 60,'
$css = $css -replace 'rgba\(240, 177, 94,', 'rgba(251, 146, 60,'
$css = $css -replace 'rgba\(240, 165, 0,', 'rgba(251, 146, 60,'
$css = $css -replace '#f0b85e', '#fb923c'
$css = $css -replace '#f0a500', '#fb923c'
$css = $css -replace '#ffd18b', '#fdba74'
$css = $css -replace '#a06a12', '#c2410c'
$css = $css -replace '#f0a500;', '#fb923c;'

# Violet deepened
$css = $css -replace 'rgba\(124, 104, 255,', 'rgba(139, 92, 246,'
$css = $css -replace 'rgba\(134, 112, 255,', 'rgba(139, 92, 246,'
$css = $css -replace '#8670ff', '#8b5cf6'
$css = $css -replace '#c4b4ff', '#c4b5fd'
$css = $css -replace '#5e46e8', '#5b21b6'
$css = $css -replace '#c2b7ff', '#c4b5fd'
$css = $css -replace 'rgba\(157, 122, 242,', 'rgba(139, 92, 246,'
$css = $css -replace '#9d7af2', '#8b5cf6'

# Background darks → deep cosmic navy
$css = $css -replace '#010305', '#04040f'
$css = $css -replace '#060d13', '#07091a'
$css = $css -replace '#010204', '#04040f'
$css = $css -replace '#030b12', '#07091a'
$css = $css -replace '#0d0f12', '#090a1e'
$css = $css -replace 'rgba\(8, 14, 20,', 'rgba(6, 8, 24,'
$css = $css -replace 'rgba\(4, 9, 15,', 'rgba(3, 5, 18,'
$css = $css -replace 'rgba\(2, 7, 12,', 'rgba(2, 4, 14,'
$css = $css -replace 'rgba\(5, 11, 17,', 'rgba(4, 6, 20,'
$css = $css -replace 'rgba\(6, 14, 22,', 'rgba(5, 8, 22,'
$css = $css -replace 'rgba\(6, 14, 20,', 'rgba(5, 8, 22,'
$css = $css -replace 'rgba\(2, 8, 14,', 'rgba(2, 5, 16,'
$css = $css -replace 'rgba\(8, 18, 24,', 'rgba(6, 8, 24,'
$css = $css -replace 'rgba\(4, 10, 15,', 'rgba(3, 5, 18,'
$css = $css -replace 'rgba\(1, 5, 8,', 'rgba(2, 3, 14,'
$css = $css -replace 'rgba\(1, 3, 6,', 'rgba(2, 3, 14,'

# gradient Shift amber same as gradient Shift (both indigo now, ok)
# sf particle colors
$css = $css -replace '#00e5c4', '#6366f1'

Set-Content $path $css -Encoding UTF8
Write-Output "Recolor complete"
