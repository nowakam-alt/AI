const defaultTasks = [
  {
    name: 'Odpowiadanie na powtarzalne maile i czaty klientów', potential: 5, risk: 2, people: 8,
    repetitions: 1800, minutes: 5, support: 70, ease: 4, data: 'high', owner: 'Lider CX',
    tool: 'Chatbot / voicebot'
  },
  {
    name: 'Podsumowywanie zgłoszeń i aktualizacja CRM', potential: 5, risk: 2, people: 10,
    repetitions: 1200, minutes: 6, support: 75, ease: 5, data: 'high', owner: 'CRM owner',
    tool: 'Automatyzacja workflow + LLM'
  },
  {
    name: 'Analiza reklamacji i przygotowanie propozycji odpowiedzi', potential: 4, risk: 4, people: 5,
    repetitions: 260, minutes: 18, support: 45, ease: 3, data: 'medium', owner: 'Specjalista reklamacji',
    tool: 'AI copilot dla konsultanta'
  },
  {
    name: 'Wyszukiwanie informacji w bazie wiedzy i regulaminach', potential: 5, risk: 3, people: 9,
    repetitions: 950, minutes: 7, support: 65, ease: 4, data: 'high', owner: 'Knowledge manager',
    tool: 'RAG / wyszukiwarka wiedzy'
  },
  {
    name: 'Tworzenie raportu jakości obsługi i trendów zapytań', potential: 4, risk: 2, people: 2,
    repetitions: 12, minutes: 180, support: 60, ease: 4, data: 'medium', owner: 'CX analyst',
    tool: 'Analityka predykcyjna'
  },
  {
    name: 'Obsługa eskalacji z silnymi emocjami klienta', potential: 2, risk: 5, people: 4,
    repetitions: 90, minutes: 35, support: 20, ease: 2, data: 'medium', owner: 'Team leader',
    tool: 'AI copilot dla konsultanta'
  },
  {
    name: 'Weryfikacja dokumentów do zwrotów i gwarancji', potential: 4, risk: 4, people: 3,
    repetitions: 300, minutes: 12, support: 45, ease: 3, data: 'medium', owner: 'Back office',
    tool: 'OCR + analiza dokumentów'
  },
  {
    name: 'Przygotowywanie komunikatów o opóźnieniach dostaw', potential: 5, risk: 2, people: 3,
    repetitions: 160, minutes: 20, support: 70, ease: 4, data: 'high', owner: 'Operations CX',
    tool: 'Generator treści'
  }
];

const recommendationMeta = {
  AUTOMATE: { label: '🟢 AUTOMATE', className: 'automate', comment: 'Automatyzuj po kontroli jakości.' },
  AUGMENT: { label: '🟡 AUGMENT', className: 'augment', comment: 'AI wspiera, człowiek zatwierdza.' },
  PROTECT: { label: '🔴 PROTECT', className: 'protect', comment: 'Zostaw decyzję człowiekowi.' },
  REDESIGN: { label: '🔵 REDESIGN', className: 'redesign', comment: 'Najpierw uprość proces.' },
  RESKILL: { label: '🔵 RESKILL', className: 'reskill', comment: 'Wymaga szkolenia i nowych zasad.' }
};

const taskRows = document.querySelector('#taskRows');
const template = document.querySelector('#taskRowTemplate');
const state = { tasks: structuredClone(defaultTasks) };

function getRecommendation(task) {
  if (task.data === 'low' && task.potential >= 4) return 'RESKILL';
  if (task.potential >= 4 && task.risk <= 2) return 'AUTOMATE';
  if (task.potential >= 4 && task.risk >= 4) return 'AUGMENT';
  if (task.potential <= 2 && task.risk >= 4) return 'PROTECT';
  if (task.ease <= 2 || task.data === 'low') return 'REDESIGN';
  if (task.potential === 3 || task.risk === 3) return 'REDESIGN';
  return task.potential > task.risk ? 'AUTOMATE' : 'AUGMENT';
}

function dataFactor(data) {
  return { high: 1, medium: 0.75, low: 0.45 }[data] ?? 0.75;
}

function savedHours(task) {
  return (task.repetitions * task.minutes * (task.support / 100)) / 60;
}

function riskAdjustedFte(tasks) {
  const fteHours = Number(document.querySelector('#fteHours').value) || 160;
  const adjustedHours = tasks.reduce((sum, task) => {
    const riskFactor = Math.max(0.25, 1 - (task.risk - 1) * 0.14);
    const easeFactor = 0.55 + task.ease * 0.09;
    return sum + savedHours(task) * riskFactor * easeFactor * dataFactor(task.data);
  }, 0);
  return adjustedHours / fteHours;
}

function quickWinScore(task) {
  return savedHours(task) * (task.potential / 5) * (task.ease / 5) * dataFactor(task.data) * (1.15 - task.risk * 0.08);
}

function protectedScore(task) {
  return task.risk * 18 + (6 - task.potential) * 8 + savedHours(task) * 0.08;
}

function formatHours(value) {
  return `${Math.round(value).toLocaleString('pl-PL')} h`;
}

function formatDecimal(value) {
  return value.toLocaleString('pl-PL', { maximumFractionDigits: 1, minimumFractionDigits: 1 });
}

function readRows() {
  state.tasks = [...taskRows.querySelectorAll('tr')].map((row) => ({
    name: row.querySelector('.task-name').value.trim() || 'Nowe zadanie',
    potential: Number(row.querySelector('.ai-potential').value),
    risk: Number(row.querySelector('.risk').value),
    people: Number(row.querySelector('.people').value) || 1,
    repetitions: Number(row.querySelector('.repetitions').value) || 0,
    minutes: Number(row.querySelector('.minutes').value) || 1,
    support: Number(row.querySelector('.support').value),
    ease: Number(row.querySelector('.ease').value),
    data: row.querySelector('.data-availability').value,
    owner: row.querySelector('.owner').value.trim() || 'Do ustalenia',
    tool: row.querySelector('.tool-type').value
  }));
}

function createRow(task) {
  const row = template.content.firstElementChild.cloneNode(true);
  const bindings = {
    '.task-name': task.name,
    '.ai-potential': task.potential,
    '.risk': task.risk,
    '.people': task.people,
    '.repetitions': task.repetitions,
    '.minutes': task.minutes,
    '.support': task.support,
    '.ease': task.ease,
    '.data-availability': task.data,
    '.owner': task.owner,
    '.tool-type': task.tool
  };

  Object.entries(bindings).forEach(([selector, value]) => {
    row.querySelector(selector).value = value;
  });

  row.addEventListener('input', updateAll);
  row.addEventListener('change', updateAll);
  row.querySelector('.delete-row').addEventListener('click', () => {
    row.remove();
    updateAll();
  });
  taskRows.append(row);
}

function renderRows(tasks = state.tasks) {
  taskRows.innerHTML = '';
  tasks.forEach(createRow);
  updateAll();
}

function setList(element, items, emptyText = 'Brak danych — dodaj lub oceń zadania.') {
  element.innerHTML = '';
  if (!items.length) {
    const li = document.createElement('li');
    li.textContent = emptyText;
    element.append(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement('li');
    li.innerHTML = item;
    element.append(li);
  });
}

function updateRowsDisplay() {
  [...taskRows.querySelectorAll('tr')].forEach((row, index) => {
    const task = state.tasks[index];
    const recommendation = getRecommendation(task);
    const meta = recommendationMeta[recommendation];
    row.querySelectorAll('output').forEach((output) => {
      const input = output.previousElementSibling;
      output.value = input.classList.contains('support') ? `${input.value}%` : input.value;
    });
    const badge = row.querySelector('.recommendation');
    badge.textContent = meta.label;
    badge.className = `badge recommendation ${meta.className}`;
    row.querySelector('.saved-hours').textContent = `${formatHours(savedHours(task))}/mies.`;
    row.querySelector('.comment').textContent = meta.comment;
  });
}

function updateInsights() {
  const tasks = state.tasks;
  const totalHours = tasks.reduce((sum, task) => sum + savedHours(task), 0);
  const fte = riskAdjustedFte(tasks);
  const readiness = tasks.length
    ? tasks.reduce((sum, task) => sum + ((task.potential + task.ease) / 10) * dataFactor(task.data), 0) / tasks.length
    : 0;
  const quickWins = [...tasks].sort((a, b) => quickWinScore(b) - quickWinScore(a)).slice(0, 3);
  const protectedTasks = [...tasks].sort((a, b) => protectedScore(b) - protectedScore(a)).slice(0, 3);
  const automateTasks = tasks.filter((task) => getRecommendation(task) === 'AUTOMATE');
  const highRiskTasks = tasks.filter((task) => task.risk >= 4);
  const department = document.querySelector('#department').value || 'dział';
  const industry = document.querySelector('#industry').value || 'branża';

  document.querySelector('#timeSaved').textContent = `${formatHours(totalHours)}/mies.`;
  document.querySelector('#heroScore').textContent = formatHours(totalHours);
  document.querySelector('#ftePotential').textContent = `${formatDecimal(fte)} etatu`;
  document.querySelector('#readiness').textContent = `${Math.round(readiness * 100)}%`;
  document.querySelector('#bestPilot').textContent = quickWins[0]?.name ?? '—';

  setList(document.querySelector('#quickWins'), quickWins.map((task) => `<strong>${task.name}</strong> — ${formatHours(savedHours(task))}/mies., właściciel: ${task.owner}.`));
  setList(document.querySelector('#protectedTasks'), protectedTasks.map((task) => `<strong>${task.name}</strong> — ryzyko ${task.risk}/5, rekomendacja: ${getRecommendation(task)}.`));
  setList(document.querySelector('#skillsList'), buildSkills(tasks));

  document.querySelector('#fteNarrative').textContent = `Wstępny potencjał redukcji lub przesunięcia pracy to ok. ${formatDecimal(fte)} FTE miesięcznie. To nie jest automatyczna rekomendacja zwolnień: wynik pokazuje pulę czasu, którą można przeznaczyć na jakość obsługi, retencję i trudne sprawy klientów.`;
  setList(document.querySelector('#redFlags'), buildRedFlags(highRiskTasks));
  document.querySelector('#managerRecommendation').textContent = quickWins.length
    ? `Zacznij od 2-tygodniowego pilota dla zadania „${quickWins[0].name}”, bo łączy wysoki wpływ, dane i łatwość wdrożenia. Równolegle ustaw zasadę: AI proponuje, człowiek odpowiada za eskalacje i decyzje sporne.`
    : 'Dodaj zadania, aby wygenerować rekomendację.';
  document.querySelector('#changeMessage').textContent = `Wprowadzamy AI w obszarze ${department} (${industry}), aby ograniczyć powtarzalne zadania i dać zespołowi więcej czasu na relacje, decyzje i odpowiedzialną obsługę klienta.`;
  document.querySelector('#pilotPlan').textContent = quickWins[0]
    ? `Pierwszy pilot: wybierz 1 zespół, ${quickWins[0].owner} jako właściciela, próbkę 100 spraw, kryteria jakości odpowiedzi i cotygodniowy przegląd błędów AI.`
    : 'Dodaj zadanie, aby zobaczyć plan pilota.';

  return { totalHours, fte, quickWins, protectedTasks, automateTasks };
}

function buildSkills(tasks) {
  const skills = new Set([
    'Praca z AI copilotem i formułowanie dobrych promptów.',
    'Rozpoznawanie halucynacji, błędnych źródeł i niepewnych odpowiedzi.',
    'Projektowanie zasad human-in-the-loop dla spraw ryzykownych.'
  ]);
  if (tasks.some((task) => task.data !== 'high')) skills.add('Porządkowanie bazy wiedzy, taksonomii zgłoszeń i jakości danych.');
  if (tasks.some((task) => task.risk >= 4)) skills.add('Ocena ryzyka prawnego, prywatności i bezpieczeństwa danych klienta.');
  if (tasks.some((task) => getRecommendation(task) === 'AUTOMATE')) skills.add('Monitorowanie automatyzacji, KPI i jakości odpowiedzi bota.');
  return [...skills];
}

function buildRedFlags(highRiskTasks) {
  const flags = [
    'Nie automatyzuj decyzji reklamacyjnych bez jasnej ścieżki akceptacji przez człowieka.',
    'Nie używaj danych klienta w narzędziach bez zatwierdzonej polityki bezpieczeństwa i retencji.',
    'Uważaj na procesy z niską dostępnością danych — AI może generować pewnie brzmiące błędy.'
  ];
  highRiskTasks.slice(0, 2).forEach((task) => flags.push(`Wysokie ryzyko w zadaniu „${task.name}” — wymagany audyt i human-in-the-loop.`));
  return flags;
}

function updateAll() {
  readRows();
  updateRowsDisplay();
  updateInsights();
}

function summaryText() {
  const { totalHours, fte, quickWins, protectedTasks } = updateInsights();
  return [
    'AI Automatyzacja — podsumowanie kalkulatora',
    `Departament: ${document.querySelector('#department').value}`,
    `Branża: ${document.querySelector('#industry').value}`,
    `Szacowana oszczędność: ${formatHours(totalHours)}/mies.`,
    `Wstępny potencjał FTE: ${formatDecimal(fte)}`,
    `Top 3 quick wins: ${quickWins.map((task) => task.name).join('; ')}`,
    `Zadania chronione: ${protectedTasks.map((task) => task.name).join('; ')}`
  ].join('\n');
}

function downloadCsv() {
  updateAll();
  const headers = ['Zadanie', 'Potencjal AI', 'Ryzyko', 'Osoby', 'Powtorzenia miesiecznie', 'Minuty', 'Wsparcie AI %', 'Latwosc', 'Dane', 'Wlasciciel', 'Rekomendacja', 'Narzedzie AI', 'Oszczednosc h'];
  const rows = state.tasks.map((task) => [
    task.name, task.potential, task.risk, task.people, task.repetitions, task.minutes, task.support,
    task.ease, task.data, task.owner, getRecommendation(task), task.tool, Math.round(savedHours(task))
  ]);
  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(','))
    .join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'ai-automatyzacja-customer-support.csv';
  link.click();
  URL.revokeObjectURL(url);
}

document.querySelector('#addTaskBtn').addEventListener('click', () => {
  createRow({
    name: 'Nowe zadanie', potential: 3, risk: 3, people: 1, repetitions: 50, minutes: 10,
    support: 40, ease: 3, data: 'medium', owner: 'Do ustalenia', tool: 'AI copilot dla konsultanta'
  });
  updateAll();
});

document.querySelector('#resetBtn').addEventListener('click', () => {
  state.tasks = structuredClone(defaultTasks);
  renderRows();
});

document.querySelector('#downloadCsvBtn').addEventListener('click', downloadCsv);
document.querySelector('#printBtn').addEventListener('click', () => window.print());
document.querySelector('#copySummaryBtn').addEventListener('click', async () => {
  const text = summaryText();
  if (navigator.clipboard) await navigator.clipboard.writeText(text);
});
['#department', '#industry', '#teamSize', '#fteHours'].forEach((selector) => {
  document.querySelector(selector).addEventListener('input', updateAll);
});

renderRows();
