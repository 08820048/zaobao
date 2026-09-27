/* AI 早报 · 单条早报一键复制 */
(function () {
  var buttons = document.querySelectorAll(".story-copy");

  // 非安全上下文（如局域网 http）下的降级方案
  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch (e) {}
    document.body.removeChild(ta);
  }

  Array.prototype.forEach.call(buttons, function (btn) {
    var story = btn.closest(".story");
    var source = story ? story.querySelector(".story-text") : null;
    var status = btn.querySelector(".copy-status");
    var timer = null;

    btn.addEventListener("click", function () {
      var text = source ? source.textContent : "";
      var markCopied = function () {
        btn.classList.add("copied");
        if (status) status.textContent = "本条早报已复制到剪贴板";
        if (timer) clearTimeout(timer);
        timer = setTimeout(function () {
          btn.classList.remove("copied");
          if (status) status.textContent = "";
        }, 1600);
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(markCopied, function () {
          fallbackCopy(text);
          markCopied();
        });
      } else {
        fallbackCopy(text);
        markCopied();
      }
    });
  });
})();
