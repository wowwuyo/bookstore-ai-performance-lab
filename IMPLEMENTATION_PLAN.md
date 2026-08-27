# Bookstore AI Performance Lab 實作計畫

依據目前專案骨架與 `bookstore-ai-performance-lab_Week7_PRD.docx` 整理。

## 實作範圍

本次實作 5 隻 API：

- `GET /health`
- `GET /inventory/{book_id}`
- `POST /orders`
- `GET /orders/{order_id}`
- `POST /orders/{order_id}/reserve`

PRD 明確列為 Out of Scope 的取消訂單與履約 API 不在本次範圍內。

## Step 1：建立執行與測試基礎

### 目標

讓專案可以安裝依賴、匯入 FastAPI 應用、執行 Ruff 與測試。

### 預計新增或修改

- `pyproject.toml`
- `requirements.txt` 或開發依賴設定
- `tests/conftest.py`
- `tests/test_app_startup.py`

### 完成後驗證

```powershell
python --version
python -m pytest tests/test_app_startup.py
ruff check .
```

驗收 Python 版本符合 3.14、應用程式可匯入、Ruff 可執行。

### 依賴

無。

## Step 2：建立資料模型與資料庫表格

### 目標

建立書籍、庫存、訂單與訂單品項的 Code First ORM 模型。

### 預計新增或修改

- `app/models/__init__.py`
- `app/models/book.py`
- `app/models/order.py`
- `app/database.py`
- `tests/test_models.py`

### 預計模型

- `Book`：`id`、`title`、`is_active`
- `Inventory`：`book_id`、`quantity`
- `Order`：`id`、`status`、`created_at`
- `OrderItem`：`order_id`、`book_id`、`quantity`

### 完成後驗證

- 啟動時可建立資料表。
- 所有 ORM model 已註冊至 `Base.metadata`。
- 訂單與品項關聯可正常建立。
- 必要欄位與約束存在。

### 依賴

依賴 Step 1。

## Step 3：建立初始測試資料

### 目標

讓服務啟動後立即有可操作的書籍與庫存資料。

### 預計新增或修改

- `app/database.py`
- `app/repositories/seed.py`
- `app/models/book.py`
- `tests/test_seed_data.py`

### 資料需求

- 至少一筆庫存充足的書籍。
- 至少一筆庫存為 0 或不足的書籍。
- 每筆書籍都有可辨識的 `book_id`。
- 重複啟動不產生重複資料。

### 完成後驗證

初始化資料庫後，確認充足庫存與不足庫存案例都存在，且 seed 可重複執行。

### 依賴

依賴 Step 2。

## Step 4：定義 Request / Response Schema

### 目標

正式定義 API 輸入、輸出與驗證規則，讓 `/docs` 顯示完整契約。

### 預計新增

- `app/schemas/__init__.py`
- `app/schemas/health.py`
- `app/schemas/inventory.py`
- `app/schemas/orders.py`
- `tests/test_schemas.py`

### 主要資料契約

`POST /orders` request：

```json
{
  "items": [
    {
      "book_id": 1,
      "quantity": 2
    }
  ]
}
```

建立訂單 response：

```json
{
  "order_id": "uuid",
  "status": "PENDING",
  "items": [
    {
      "book_id": 1,
      "quantity": 2
    }
  ]
}
```

庫存 response：

```json
{
  "book_id": 1,
  "available_quantity": 10
}
```

### 驗證規則

- 訂單至少包含一個品項。
- `quantity` 必須大於 0。
- `book_id` 必須是有效整數。
- 訂單狀態限制為 `PENDING` 或 `RESERVED`。

### 完成後驗證

- 空品項清單回傳驗證錯誤。
- `quantity = 0` 或負數回傳驗證錯誤。
- 合法 payload 可通過 Pydantic 驗證。
- OpenAPI `/docs` 顯示 request / response schema。

### 依賴

依賴 Step 2；可與 Step 3 平行執行。

## Step 5：建立 Repository 資料存取層

### 目標

集中處理書籍、庫存與訂單的資料庫讀寫，避免 router 直接操作 SQLAlchemy。

### 預計新增

- `app/repositories/__init__.py`
- `app/repositories/books.py`
- `app/repositories/inventory.py`
- `app/repositories/orders.py`
- `tests/repositories/test_books.py`
- `tests/repositories/test_orders.py`
- `tests/repositories/test_inventory.py`

### 預計功能

- 依 `book_id` 查詢書籍與庫存。
- 建立訂單與訂單品項。
- 依 `order_id` 查詢訂單。
- 讀取與更新庫存數量。
- 更新訂單狀態。

### 完成後驗證

驗證存在與不存在資料的查詢結果、訂單及品項的儲存讀取，以及庫存更新後數值。

### 依賴

依賴 Step 2；建議在 Step 3 後執行。

## Step 6：實作訂單與庫存服務邏輯

### 目標

實作 PRD 核心商業規則，尤其是庫存預留的全有或全無行為。

### 預計新增

- `app/services/__init__.py`
- `app/services/order_service.py`
- `app/services/inventory_service.py`
- `tests/services/test_order_service.py`
- `tests/services/test_reservation_service.py`

### 核心規則

1. 建立訂單時至少要有一個品項。
2. 建立訂單不扣庫存。
3. 新訂單狀態為 `PENDING`。
4. 只有 `PENDING` 訂單可以預留。
5. 任一品項庫存不足，整筆預留失敗。
6. 預留失敗時不得扣除任何品項庫存。
7. 預留成功後狀態變更為 `RESERVED`。
8. `RESERVED` 訂單不可再次扣庫存。

### 完成後驗證

- 建立訂單後庫存不變。
- 預留成功後庫存正確減少。
- 預留成功後狀態為 `RESERVED`。
- 庫存不足時整筆交易回滾。
- 多品項訂單不會部分扣庫存。
- 重複預留回傳 invalid state 錯誤。

### 依賴

依賴 Step 4 與 Step 5。

## Step 7：實作 FastAPI Routers

### 目標

將服務邏輯公開成可操作的 API，並補上目前 `main.py` 已引用但尚不存在的 router。

### 預計新增

- `app/routers/__init__.py`
- `app/routers/system.py`
- `app/routers/inventory.py`
- `app/routers/orders.py`
- `tests/routers/test_health.py`
- `tests/routers/test_inventory.py`
- `tests/routers/test_orders.py`

### 預計修改

- `app/main.py`
- `app/observability.py`

### 實作 API

- `GET /health`
- `GET /inventory/{book_id}`
- `POST /orders`
- `GET /orders/{order_id}`
- `POST /orders/{order_id}/reserve`

保留既有 observability 基礎設定，但不實作 PRD 範圍外的取消與履約 API。

### 完成後驗證

```powershell
python -m pytest tests/routers
uvicorn app.main:app --reload
```

確認 `/docs` 可開啟、所有 API 出現在 OpenAPI 文件，且不存在的書籍與訂單使用既有錯誤 envelope。

### 依賴

依賴 Step 4、Step 5、Step 6。

## Step 8：端對端驗收與品質檢查

### 目標

依 PRD 使用情境，驗證從建立訂單到預留庫存的完整流程。

### 預計新增或修改

- `tests/integration/test_order_reservation_flow.py`
- `README.md`
- `pyproject.toml`，如需補充 Ruff 或 pytest 設定

### 完成後驗證流程

1. 查詢初始庫存，例如 `10`。
2. 建立包含 2 本書的訂單。
3. 確認訂單狀態為 `PENDING`。
4. 確認建立訂單後庫存仍為 `10`。
5. 執行庫存預留。
6. 確認訂單狀態變成 `RESERVED`。
7. 確認庫存變成 `8`。
8. 使用不足庫存商品建立訂單並執行預留。
9. 確認預留失敗且庫存沒有部分扣除。

### 完整驗證指令

```powershell
python -m pytest
ruff check .
ruff format --check .
```

並人工確認：

```text
http://127.0.0.1:8000/docs
```

### 依賴

依賴 Step 1 至 Step 7。

## 步驟依賴圖

```text
Step 1
  └── Step 2
        ├── Step 3
        ├── Step 4
        └── Step 5
              └── Step 6
                    └── Step 7
                          └── Step 8
```

Step 3 與 Step 4 可在 Step 2 完成後平行進行；Step 7 必須等 Schema、Repository 與 Service 完成後才能整合。
