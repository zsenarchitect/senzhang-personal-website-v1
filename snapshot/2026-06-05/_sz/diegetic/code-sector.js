(function () {
  var root = document.documentElement;
  root.classList.add("sz-diegetic-code");

  var svg =
    '<svg class="sz-crt-filters" aria-hidden="true" width="0" height="0" style="position:absolute">' +
    '<filter id="sz-crt-rgb-split" color-interpolation-filters="sRGB">' +
    '<feOffset in="SourceGraphic" dx="1.2" dy="0" result="r"/>' +
    '<feOffset in="SourceGraphic" dx="-1.2" dy="0" result="b"/>' +
    '<feBlend in="r" in2="SourceGraphic" mode="screen" result="rb"/>' +
    '<feBlend in="b" in2="rb" mode="screen"/>' +
    "</filter></svg>";
  document.body.insertAdjacentHTML("beforeend", svg);

  var btn = document.createElement("button");
  btn.type = "button";
  btn.className = "sz-plain-view-toggle";
  btn.textContent = "Plain view";
  btn.setAttribute("aria-pressed", "false");
  btn.addEventListener("click", function () {
    var on = root.classList.toggle("sz-plain-view");
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    btn.textContent = on ? "CRT view" : "Plain view";
  });
  document.body.appendChild(btn);
})();
