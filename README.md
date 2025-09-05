# PyBitTorrent Client

یک کلاینت BitTorrent کامل نوشته شده با Python که تمام قابلیت‌های اصلی پروتکل BitTorrent را پیاده‌سازی می‌کند.

## ویژگی‌ها

- خواندن فایل‌های torrent (bencode parsing)
- اتصال به tracker های HTTP و UDP
- اتصال به peer ها و مدیریت ارتباط
- درخواست و دریافت block ها از peer ها
- مدیریت piece ها و تایید hash
- پشتیبانی از torrent های تک فایل و چند فایل
- قابلیت seed کردن به peer های دیگر
- مدیریت حافظه و نوشتن بر روی دیسک

## نحوه استفاده

### اجرای ساده
\`\`\`bash
python scripts/run_client.py path/to/your/torrent/file.torrent
\`\`\`

### اجرای دستی
\`\`\`bash
python scripts/bittorrent_client.py path/to/your/torrent/file.torrent
\`\`\`

## ساختار پروژه

- `torrent_parser.py` - پارس کردن فایل‌های torrent و bencode
- `tracker_client.py` - ارتباط با tracker های HTTP/UDP
- `peer_connection.py` - مدیریت اتصال به peer ها
- `piece_manager.py` - مدیریت piece ها و نوشتن فایل‌ها
- `bittorrent_client.py` - کلاینت اصلی
- `run_client.py` - اسکریپت اجرای ساده

## جزئیات پیاده‌سازی

### پارس کردن Torrent
- پیاده‌سازی کامل bencode decoder/encoder
- استخراج metadata شامل announce URL، piece length، file list
- محاسبه info_hash برای شناسایی torrent

### ارتباط با Tracker
- پشتیبانی از HTTP/HTTPS trackers
- پشتیبانی از UDP trackers
- مدیریت announce list و fallback trackers

### مدیریت Peer
- handshake protocol
- پیام‌های BitTorrent (choke, unchoke, interested, have, bitfield, request, piece)
- مدیریت concurrent connections
- request pipelining برای بهبود سرعت

### مدیریت Piece
- تقسیم piece ها به block های 16KB
- تایید hash هر piece
- مدیریت حافظه و flush کردن به دیسک
- پشتیبانی از multi-file torrents

## محدودیت‌ها و نکات

- از کتابخانه‌های استاندارد Python استفاده می‌کند
- پیاده‌سازی کامل پروتکل BitTorrent بدون dependency خارجی
- مناسب برای یادگیری و درک عمیق پروتکل BitTorrent
- قابل توسعه برای ویژگی‌های پیشرفته‌تر

## مثال خروجی

\`\`\`
=== PyBitTorrent Client ===
Loading torrent file: ubuntu.torrent
Loaded torrent: ubuntu-20.04.3-desktop-amd64.iso
Total size: 3379068928 bytes
Pieces: 1612
Files: 1
Download started!
Connected to peer: 192.168.1.100:51413
Received block: piece 0, offset 0
Completed piece 0/1612
Progress: 0.1% | Active peers: 3
Progress: 15.2% | Peers: 5/12 | Remaining: 2865432576 bytes
\`\`\`

این پیاده‌سازی تمام requirements پروژه شما را برآورده می‌کند و یک کلاینت BitTorrent کاملاً کاربردی ارائه می‌دهد.
