let selectedRole = null;
let gameData = null;

async function initGame() {
    const response = await fetch('/init');
    gameData = await response.json();
    // 更新案件背景顯示
    document.getElementById('case-info').innerText = 
        `${gameData.case.case_type}發生在${gameData.case.location}，時間是${gameData.case.time}，受害者是${gameData.case.victim}。`;
    
    // 更新角色按鈕
    const roleButtons = document.getElementById('role-buttons');
    Object.keys(gameData.roles).forEach(role => {
        const btn = document.createElement('button');
        btn.innerText = role;  // 只顯示角色名稱，不顯示性格
        btn.onclick = () => selectRole(role, btn);
        roleButtons.appendChild(btn);
    });

    // 顯示圖像
    document.getElementById('story-image').src = gameData.image_url;
}

function selectRole(role, btn) {
    selectedRole = role;
    document.querySelectorAll('#role-buttons button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

async function sendQuestion() {
    if (!selectedRole) {
        alert('請先選擇一個角色！');
        return;
    }
    const question = document.getElementById('question').value;
    if (!question) return;
    const chatArea = document.getElementById('chat-area');
    chatArea.value += `你問 ${selectedRole}：${question}\n`;
    const response = await fetch('/talk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: selectedRole, question })
    });
    const data = await response.json();
    chatArea.value += `${selectedRole} 說：${data.response}\n\n\n`;
    chatArea.scrollTop = chatArea.scrollHeight;
    document.getElementById('question').value = '';
}

async function guessKiller() {
    const guess = prompt('你認為兇手是誰？');
    if (!guess) return;
    const response = await fetch('/guess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ guess })
    });
    const data = await response.json();
    const modalText = document.getElementById('modal-text');
    modalText.innerText = data.correct ? 
        `恭喜你！${guess} 是兇手！\n案件總結：${data.summary}` : 
        `錯了！${guess} 不是兇手。\n案件總結：${data.summary}`;
    document.getElementById('modal').style.display = 'block';
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
    location.reload(); // 重啟遊戲
}

window.onload = initGame;