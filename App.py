import pandas as pd
import requests
import streamlit as st

# Thay bằng link HTTP POST URL thực tế từ Power Automate của bạn
POWER_AUTOMATE_URL = "https://default6ea838f0f529455e9738147060990b.55.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/06/workflows/0de2189ff31d4c25bb26b407c88c9cf2/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=9cxv3EUDO0hLp5WByTrc7IEWLpmD9mCn2Yw-Rh1qipg"


def lay_data_tu_power_automate():
  """Hàm gửi request đến Power Automate và trả về DataFrame kèm thông báo lỗi (nếu có)."""
  try:
    with st.spinner("⏳ Đang kết nối và lấy dữ liệu từ Power Automate..."):
      response = requests.post(POWER_AUTOMATE_URL, json={}, timeout=30)

      if response.status_code == 200:
        data = response.json()

        # Kiểm tra nếu dữ liệu nằm trong trường 'value' (định dạng thường gặp từ SharePoint)
        if isinstance(data, dict) and "value" in data:
          records = data["value"]
        elif isinstance(data, list):
          records = data
        else:
          records = [data]

        df = pd.DataFrame(records)
        return df, None
      else:
        return (
            None,
            f"Lỗi phản hồi HTTP {response.status_code}: {response.text}",
        )
  except requests.exceptions.Timeout:
    return None, "Hết thời gian chờ (Timeout) khi gọi Power Automate."
  except Exception as e:
    return None, f"Lỗi kết nối: {str(e)}"


# ==========================================
# GIAO DIỆN STREAMLIT
# ==========================================
st.title("🔄 Đồng Bộ Dữ Liệu Từ Power Automate")

# 1. Nút bấm kích hoạt lấy dữ liệu
col_btn, col_info = st.columns([2, 5])
with col_btn:
  btn_lay_du_lieu = st.button(
      "📥 Lấy Dữ Liệu Ngay", type="primary", use_container_width=True
  )

# 2. Xử lý khi nhấn nút
if btn_lay_du_lieu:
  df_result, err = lay_data_tu_power_automate()

  if err:
    st.error(f"❌ Không lấy được dữ liệu: {err}")
  elif df_result is not None and not df_result.empty:
    st.success(
        f"✅ Lấy dữ liệu thành công! Tìm thấy **{len(df_result)}** bản ghi."
    )

    # Hiển thị số liệu tổng quan
    c1, c2 = st.columns(2)
    c1.metric("Tổng số dòng", len(df_result))
    c2.metric("Số cột dữ liệu", len(df_result.columns))

    st.markdown("---")
    st.subheader("📋 Danh Sách Dữ Liệu Chi Tiết")

    # Hiển thị bảng dữ liệu (Interactive Table)
    st.dataframe(df_result, use_container_width=True)

    # Tùy chọn xem từng dòng dạng danh sách mở rộng (Expander)
    with st.expander("🔍 Xem chi tiết từng bản ghi dạng danh sách thẻ"):
      for idx, row in df_result.iterrows():
        st.markdown(f"**Bản ghi #{idx + 1}**")
        st.json(row.to_dict())
        st.divider()
  else:
    st.warning("⚠️ Kết nối thành công nhưng không có dữ liệu trả về (Rỗng).")
else:
  st.info("👆 Nhấn nút **'Lấy Dữ Liệu Ngay'** ở trên để tải danh sách mới nhất.")