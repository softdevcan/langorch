# 🚀 START HERE - LangOrch v0.1 MVP

## ✅ Hazırlık Tamamlandı!

Tüm gerekli kurulumlar yapıldı:
- ✅ Database migrations çalıştırıldı
- ✅ Test users oluşturuldu
- ✅ email-validator yüklendi
- ✅ Docker services çalışıyor

---

## 🎯 Backend Başlatma

**ÖNEMLİ:** Backend'i `backend` klasörünün **içinden** başlatmalısın:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend başarıyla çalıştığında göreceksin:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Test Et:**
- 🌐 http://localhost:8000 - Backend API
- 📚 http://localhost:8000/api/v1/docs - API Documentation

---

## 🎨 Frontend Başlatma

**Yeni bir terminal aç** ve:

```bash
cd frontend
npm run dev
```

✅ Frontend başarıyla çalıştığında göreceksin:
```
- Local:   http://localhost:3000
```

---

## 🎉 Uygulamayı Kullan

1. **Tarayıcıda aç:** http://localhost:3000

2. **Login yap:**
   - Email: `admin@test.com`
   - Password: `admin123`

3. **Özellikleri test et:**
   - ✅ Dashboard görüntüle
   - ✅ Users menüsüne git
   - ✅ Yeni kullanıcı ekle
   - ✅ Kullanıcı düzenle/sil
   - ✅ Logout yap

---

## 🐛 Sorun Giderme

### "No module named 'app'" Hatası
❌ **Yanlış:** Root klasörden `uvicorn app.main:app` çalıştırma
✅ **Doğru:** `cd backend` yap, sonra çalıştır

### Port Zaten Kullanımda
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Database Bağlantı Hatası
Docker servisleri çalışıyor mu kontrol et:
```bash
docker ps | grep langorch
```

---

## 📊 Test Kullanıcıları

Database'de hazır 2 kullanıcı var:

| Email | Password | Role | Açıklama |
|-------|----------|------|----------|
| admin@test.com | admin123 | TENANT_ADMIN | Full access |
| user@test.com | user123 | USER | Basic access |

---

## 🎯 Hızlı Komutlar

```bash
# Backend başlat
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend başlat (yeni terminal)
cd frontend && npm run dev

# Database kontrol
docker exec langorch_postgres psql -U langorch -d langorch -c "SELECT email, role FROM users;"

# Test users tekrar oluştur
cd backend && python scripts/seed_test_data.py
```

---

## 📚 Dokümantasyon

- [VERSION_0.1_SUMMARY.md](VERSION_0.1_SUMMARY.md) - Complete summary
- [QUICK_START.md](QUICK_START.md) - Detailed setup guide
- [TESTING_GUIDE.md](docs/TESTING_GUIDE.md) - Test scenarios
- [DEVELOPMENT_ROADMAP.md](docs/development-phases/DEVELOPMENT_ROADMAP.md) - Roadmap

---

## ✨ Sonraki Adımlar

Version 0.1 MVP tamamlandı! 🎉

**Version 0.2** için hazır:
- Row Level Security (PostgreSQL RLS)
- HashiCorp Vault integration
- Document upload & embedding
- Vector search (pgvector + Qdrant)

---

**💡 İpucu:** Her iki servisi de aynı anda çalıştırmak için 2 terminal penceresi kullan!

**Başarılar! 🚀**
