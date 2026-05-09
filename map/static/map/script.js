document.addEventListener('DOMContentLoaded', function () {
    const actionBtn = document.getElementById('actionBtn');
    if (actionBtn) {
        actionBtn.addEventListener('click', function () {
            alert('Map 관리 페이지 버튼을 클릭했습니다.');
        });
    }
});
