"use strict";
const $ = (id) => document.getElementById(id);
const input = $("file-input"), analyze = $("analyze");
let selected = null, previewURL = null, ready = false, busy = false;
function showError(message) { $("error").textContent = message; $("error").hidden = !message; }
function updateButton() { analyze.disabled = !selected || !ready || busy; }
function clearResult() { $("results").hidden = true; $("empty-result").hidden = false; }
function clearSelection() {
  if (previewURL) URL.revokeObjectURL(previewURL);
  previewURL = null; selected = null; input.value = "";
  $("preview").hidden = true; $("preview").removeAttribute("src");
  $("upload-hint").hidden = false; $("file-info").hidden = true;
  clearResult(); showError(""); updateButton();
}
function selectFile(file) {
  if (busy) return;
  clearSelection();
  if (!file) return;
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) return showError("JPG, PNG, WebP 이미지 파일을 선택해 주세요.");
  if (file.size > 10 * 1024 * 1024) return showError("파일은 10MB 이하여야 합니다.");
  if (file.size === 0) return showError("비어 있는 파일입니다. 이미지를 다시 선택해 주세요.");
  selected = file; previewURL = URL.createObjectURL(file);
  $("preview").src = previewURL; $("preview").hidden = false;
  $("upload-hint").hidden = true; $("file-info").hidden = false;
  $("file-name").textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB`;
  updateButton();
}
$("preview").addEventListener("error", () => {
  clearSelection(); showError("이미지 미리보기를 읽을 수 없습니다. 손상되지 않은 파일을 선택해 주세요.");
});
input.addEventListener("change", () => selectFile(input.files[0]));
$("reset").addEventListener("click", clearSelection);
for (const event of ["dragenter", "dragover"]) $("drop-zone").addEventListener(event, (e) => {
  e.preventDefault(); if (!busy) $("drop-zone").classList.add("dragging");
});
for (const event of ["dragleave", "drop"]) $("drop-zone").addEventListener(event, (e) => {
  e.preventDefault(); $("drop-zone").classList.remove("dragging");
});
$("drop-zone").addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length !== 1) return showError("이미지는 한 번에 한 개씩 선택해 주세요.");
  selectFile(e.dataTransfer.files[0]);
});
async function checkHealth() {
  try {
    const response = await fetch("/api/health", { signal: AbortSignal.timeout(10000) });
    const health = await response.json(); ready = response.ok && health.ready;
    $("status").textContent = ready ? "모델 준비 완료 · 사진은 외부로 전송되지 않습니다." : "모델 준비 필요 · 서버 로그와 준비 명령을 확인해 주세요.";
  } catch { ready = false; $("status").textContent = "서버에 연결할 수 없습니다. python run.py 실행 상태를 확인해 주세요."; }
  updateButton();
}
function render(result) {
  const top = result.predictions[0];
  $("top-name").textContent = top.name_ko; $("top-label").textContent = top.label;
  $("top-score").textContent = `${(top.score * 100).toFixed(1)}%`;
  $("candidates").replaceChildren();
  for (const [index, candidate] of result.predictions.entries()) {
    const row = document.createElement("div"); row.className = "candidate";
    const heading = document.createElement("div"); heading.className = "candidate-label";
    const name = document.createElement("span"); name.textContent = `${index + 1}. ${candidate.name_ko}`;
    const score = document.createElement("span"); score.textContent = `${(candidate.score * 100).toFixed(1)}%`;
    const label = document.createElement("small"); label.textContent = candidate.label;
    const meter = document.createElement("progress"); meter.className = "meter"; meter.max = 1; meter.value = candidate.score; meter.setAttribute("aria-label", `${candidate.name_ko} 모델 상대 점수`);
    heading.append(name, score); row.append(heading, label, meter); $("candidates").append(row);
  }
  $("timing").textContent = `${result.image_size.join(" × ")} px · ${(result.elapsed_ms / 1000).toFixed(2)}초 · CPU`;
  $("uncertain").hidden = !result.uncertain;
  $("empty-result").hidden = true; $("results").hidden = false;
}
analyze.addEventListener("click", async () => {
  if (!selected || busy) return;
  busy = true; updateButton(); clearResult(); showError("");
  input.disabled = true; $("reset").disabled = true;
  $("result-card").setAttribute("aria-busy", "true");
  $("status").textContent = "잎과 형태를 살펴보고 있습니다…";
  analyze.textContent = "분석 중…";
  const data = new FormData(); data.append("file", selected);
  try {
    const response = await fetch("/api/analyze", { method: "POST", body: data, signal: AbortSignal.timeout(120000) });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "이미지 요청을 처리할 수 없습니다.");
    render(result); $("status").textContent = "분석 완료 · 결과는 추정치입니다.";
  } catch (error) {
    const network = error.name === "TypeError";
    showError(network ? "서버 연결이 끊겼습니다. python run.py 실행 상태를 확인한 뒤 다시 시도해 주세요." : error.name === "TimeoutError" ? "분석 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요." : error.message);
    $("status").textContent = "분석하지 못했습니다. 오류 안내를 확인해 주세요.";
  } finally {
    busy = false; input.disabled = false; $("reset").disabled = false;
    analyze.textContent = "식물 후보 분석하기 ↗"; updateButton();
    $("result-card").setAttribute("aria-busy", "false");
  }
});
checkHealth();
