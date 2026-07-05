const video = document.getElementById("webcam");
const canvas = document.getElementById("capture");
const scanButton = document.getElementById("scan-btn");
const retryButton = document.getElementById("retry-btn");
const statusText = document.getElementById("status-text");
const spinner = document.getElementById("spinner");
const successBox = document.getElementById("success");
const qrButton = document.getElementById("qr-btn");

let stream = null;
let isInitializing = false;

const setStatus = (message) => {
  if (statusText) statusText.textContent = message;
};

const setLoading = (loading) => {
  if (spinner) spinner.style.display = loading ? "block" : "none";
  if (scanButton) scanButton.disabled = loading;
};

const showRetry = (show) => {
  if (retryButton) retryButton.style.display = show ? "inline-block" : "none";
};

const showSuccess = (show) => {
  if (successBox) successBox.style.display = show ? "block" : "none";
};

const stopStream = () => {
  if (!stream) return;
  stream.getTracks().forEach((track) => track.stop());
  stream = null;
};

const initCamera = async () => {
  if (isInitializing) return;
  isInitializing = true;
  
  if (scanButton) scanButton.disabled = true;
  showRetry(false);
  setStatus("Requesting Camera Permission...");

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setStatus("Camera API not supported in this browser.");
    isInitializing = false;
    showRetry(true);
    return;
  }

  stopStream();

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: false,
    });
    
    if (video) {
      video.srcObject = stream;
      video.muted = true; // Ensure it can autoplay
      video.onloadedmetadata = async () => {
        try {
          await video.play();
          setStatus("Camera Connected. Ready to scan.");
          if (scanButton) scanButton.disabled = false;
        } catch (e) {
          console.error("Error playing video", e);
          setStatus("Camera feed blocked. Please interact with the page.");
          showRetry(true);
        }
      };
    }
  } catch (error) {
    console.error("Camera error", error);
    if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
      setStatus("Camera permission denied. Please allow access.");
    } else if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
      setStatus("No camera detected on this device.");
    } else {
      setStatus("Failed to access camera.");
    }
    showRetry(true);
  } finally {
    isInitializing = false;
  }
};

const captureFrame = () => {
  if (!video || !canvas) return null;
  const width = video.videoWidth || 640;
  const height = video.videoHeight || 480;
  if (width === 0 || height === 0) return null;
  
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  context.drawImage(video, 0, 0, width, height);
  return canvas.toDataURL("image/jpeg", 0.9);
};

const scanFace = async () => {
  if (!stream) {
    setStatus("Initializing Camera...");
    await initCamera();
    if (!stream) return;
  }

  const imageData = captureFrame();
  if (!imageData) {
    setStatus("Failed to capture image. Retrying...");
    showRetry(true);
    return;
  }

  setLoading(true);
  showRetry(false);
  showSuccess(false);
  setStatus("Scanning Face...");

  try {
    const response = await window.apiFetch("/attendance/face-scan", {
      method: "POST",
      body: JSON.stringify({ image: imageData }),
    });
    
    if (!response) {
      setStatus("Session expired. Please login again.");
      showRetry(true);
      return;
    }
    
    const data = await response.json();
    if (response.ok && data.success) {
      setStatus(data.message || "Attendance marked successfully!");
      showSuccess(true);
      if (scanButton) scanButton.style.display = "none";
      stopStream();
      
      // Update streak cache dynamically to reflect scan instantly on dashboard
      const cached = sessionStorage.getItem("streak_data_cache");
      if (cached) {
         sessionStorage.removeItem("streak_data_cache");
      }

      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 1500);
      return;
    }
    
    setStatus(data.message || "Face not recognized. Try again.");
    showRetry(true);
  } catch (error) {
    console.error("Scan failed", error);
    setStatus("Network error. Please retry.");
    showRetry(true);
  } finally {
    setLoading(false);
  }
};

if (scanButton) scanButton.addEventListener("click", scanFace);
if (retryButton) retryButton.addEventListener("click", scanFace);
if (qrButton) qrButton.addEventListener("click", () => {
  stopStream();
  window.location.href = "/dashboard";
});

window.addEventListener("beforeunload", stopStream);

document.addEventListener("DOMContentLoaded", initCamera);
