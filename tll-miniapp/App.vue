<script>
export default {
  onLaunch: function () {
  },
  onShow: function () {
  },
  onHide: function () {
  }
}
</script>

<style>
@import "@/assets/uni.css";

page {
  height: 100%;
  background-color: #f5f5f5;
  --themeColor: #ce4031;
}

image {
  width: 100%;
}

image {
  will-change: transform
}

::-webkit-scrollbar {
  display: none;
}

body {
  --primary: #007bff;
  --secondary: #6c757d;
  --success: #28a745;
  --danger: #dc3545;
  --warning: #ffc107;
  --info: #17a2b8;
  --light: #f8f9fa;
  --dark: #343a40;
  --muted: #6c757d;
  --white: #fff;
  --black: #000;
  --grey: #999;
  --borderColor: #dee2e6;
  --lightmuted: #B2B2B2;
}

.empty-items {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 0;
}

.empty-text {
  font-size: 28rpx;
  color: #999;
  margin: 32rpx 0;
}
</style>
