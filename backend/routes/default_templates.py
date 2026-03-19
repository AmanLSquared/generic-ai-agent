"""
Canonical Jinja2 templates for Asana dashboards.
These are ALWAYS used for scope-based generation (project / user) — no AI involved.
AI is only used for /continue (refinements after initial generation).

Variables are NEVER hardcoded — every value is a {{ jinja2_key }}.
"""

DEFAULT_PROJECT_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{ project.name }} – Project Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --primary: #3b82f6;
      --secondary: #f1f5f9;
      --accent: #f59e42;
      --success: #22c55e;
      --danger: #ef4444;
      --card-bg: #fff;
      --text: #1e293b;
      --muted: #64748b;
      --shadow: 0 2px 16px 0 rgba(30,41,59,0.07);
      --border-radius: 16px;
      --gap: 2rem;
    }
    body {
      background: var(--secondary);
      font-family: 'Inter', Arial, sans-serif;
      color: var(--text);
      margin: 0;
      padding: 0;
      min-height: 100vh;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 2rem 1rem;
      display: flex;
      flex-direction: column;
      gap: var(--gap);
    }
    .dashboard-structure { display: flex; flex-direction: column; gap: var(--gap); }
    .header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 1rem; }
    .header-info { display: flex; flex-direction: column; gap: 0.5rem; }
    .project-title { font-size: 2.2rem; font-weight: 700; margin: 0; color: var(--primary); }
    .workspace-name { font-size: 1rem; color: var(--muted); font-weight: 500; }
    .project-meta { display: flex; gap: 1.5rem; flex-wrap: wrap; align-items: center; margin-top: 0.5rem; }
    .project-status {
      font-size: 1rem; font-weight: 600; padding: 0.3em 1em;
      border-radius: 999px; background: var(--secondary);
      color: var(--primary); border: 1px solid var(--primary); display: inline-block;
    }
    .project-due { font-size: 1rem; color: var(--muted); font-weight: 500; }
    .team-members { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
    .member-badge {
      background: var(--primary); color: #fff; border-radius: 999px;
      padding: 0.2em 0.9em; font-size: 0.95rem; font-weight: 500;
      box-shadow: 0 1px 4px 0 rgba(59,130,246,0.08);
    }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1.5rem; }
    .kpi-card {
      background: var(--card-bg); border-radius: var(--border-radius);
      box-shadow: var(--shadow); padding: 1.5rem 1.2rem;
      display: flex; flex-direction: column; align-items: flex-start; gap: 0.5rem; min-width: 0;
    }
    .kpi-label { font-size: 1rem; color: var(--muted); font-weight: 500; }
    .kpi-value { font-size: 2.1rem; font-weight: 700; color: var(--text); margin-bottom: 0.25rem; }
    .kpi-rate { font-size: 1.1rem; font-weight: 600; color: var(--success); }
    .kpi-overdue { color: var(--danger); }
    .dashboard-sections { display: flex; flex-direction: column; gap: var(--gap); }
    .dashboard-row { display: flex; flex-wrap: wrap; gap: var(--gap); width: 100%; }
    .dashboard-col { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; gap: 1.5rem; }
    .charts-section { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 2rem; align-items: stretch; }
    .chart-card {
      background: var(--card-bg); border-radius: var(--border-radius);
      box-shadow: var(--shadow); padding: 1.5rem 1.2rem;
      display: flex; flex-direction: column; gap: 1rem; min-width: 0;
    }
    .chart-title { font-size: 1.1rem; font-weight: 600; color: var(--muted); margin-bottom: 0.5rem; }
    .tasks-section {
      background: var(--card-bg); border-radius: var(--border-radius);
      box-shadow: var(--shadow); padding: 1.5rem 1.2rem;
      margin-bottom: 2rem; overflow-x: auto;
    }
    .tasks-title { font-size: 1.3rem; font-weight: 700; margin-bottom: 1rem; color: var(--primary); }
    table.tasks-table { width: 100%; border-collapse: collapse; min-width: 700px; }
    table.tasks-table th, table.tasks-table td { padding: 0.75em 0.5em; text-align: left; }
    table.tasks-table th {
      color: var(--muted); font-size: 1rem; font-weight: 600;
      border-bottom: 2px solid var(--secondary); background: #f8fafc;
    }
    table.tasks-table tr { transition: background 0.15s; }
    table.tasks-table tr:hover { background: #f1f5f9; }
    table.tasks-table td { font-size: 1rem; border-bottom: 1px solid #f1f5f9; }
    .task-completed { color: var(--success); font-weight: 600; }
    .task-incomplete { color: var(--danger); font-weight: 600; }
    .task-tags { display: flex; gap: 0.3rem; flex-wrap: wrap; }
    .tag-badge {
      background: var(--accent); color: #fff; border-radius: 999px;
      padding: 0.15em 0.8em; font-size: 0.92rem; font-weight: 500;
    }
    @media (max-width: 900px) {
      .charts-section { grid-template-columns: 1fr; }
      .kpi-grid { grid-template-columns: 1fr 1fr; }
      .dashboard-row { flex-direction: column; }
    }
    @media (max-width: 600px) {
      .container { padding: 1rem 0.2rem; }
      .header { flex-direction: column; align-items: flex-start; gap: 0.7rem; }
      .kpi-grid { grid-template-columns: 1fr; }
    }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <div class="container">
    <div class="dashboard-structure">

      <!-- Header -->
      <div class="header">
        <div class="header-info">
          <div class="workspace-name">{{ workspace.name }}</div>
          <h1 class="project-title">{{ project.name }}</h1>
          <div class="project-meta">
            {% if project.status %}
              <span class="project-status">{{ project.status }}</span>
            {% endif %}
            {% if project.due_date %}
              <span class="project-due">Due: {{ project.due_date }}</span>
            {% endif %}
            <div class="team-members">
              {% for m in project.team_members %}
                <span class="member-badge">{{ m }}</span>
              {% endfor %}
            </div>
          </div>
        </div>
      </div>

      <div class="dashboard-sections">
        <!-- KPI Cards -->
        <div class="dashboard-row">
          <div class="dashboard-col">
            <div class="kpi-grid">
              <div class="kpi-card">
                <span class="kpi-label">Total Tasks</span>
                <span class="kpi-value">{{ summary.total_tasks }}</span>
              </div>
              <div class="kpi-card">
                <span class="kpi-label">Completed</span>
                <span class="kpi-value">{{ summary.completed_tasks }}</span>
              </div>
              <div class="kpi-card">
                <span class="kpi-label">Overdue</span>
                <span class="kpi-value kpi-overdue">{{ summary.overdue_tasks }}</span>
              </div>
              <div class="kpi-card">
                <span class="kpi-label">Completion Rate</span>
                <span class="kpi-value kpi-rate">{{ summary.completion_rate }}%</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Charts -->
        <div class="dashboard-row">
          <div class="dashboard-col">
            <div class="charts-section">
              <div class="chart-card">
                <div class="chart-title">Task Completion</div>
                <canvas id="completionChart"></canvas>
              </div>
              <div class="chart-card">
                <div class="chart-title">Team Member Workload</div>
                <canvas id="workloadChart"></canvas>
              </div>
            </div>
          </div>
        </div>

        <!-- Tasks Table -->
        <div class="dashboard-row">
          <div class="dashboard-col">
            <div class="tasks-section">
              <div class="tasks-title">Tasks</div>
              <table class="tasks-table">
                <thead>
                  <tr>
                    <th>Task</th>
                    <th>Assignee</th>
                    <th>Due Date</th>
                    <th>Status</th>
                    <th>Tags</th>
                  </tr>
                </thead>
                <tbody>
                  {% for t in tasks %}
                  <tr>
                    <td>{{ t.name }}</td>
                    <td>{% if t.assignee %}{{ t.assignee }}{% else %}–{% endif %}</td>
                    <td>{% if t.due_date %}{{ t.due_date }}{% else %}–{% endif %}</td>
                    <td>
                      {% if t.completed %}
                        <span class="task-completed">Completed</span>
                      {% else %}
                        <span class="task-incomplete">Incomplete</span>
                      {% endif %}
                    </td>
                    <td>
                      <div class="task-tags">
                        {% for tag in t.tags %}
                          <span class="tag-badge">{{ tag }}</span>
                        {% endfor %}
                      </div>
                    </td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>

  <script>
    // Task Completion Doughnut
    new Chart(document.getElementById('completionChart').getContext('2d'), {
      type: 'doughnut',
      data: {
        labels: ['Completed', 'Incomplete'],
        datasets: [{
          data: [{{ summary.completed_tasks }}, {{ summary.incomplete_tasks }}],
          backgroundColor: ['#22c55e', '#ef4444'],
          borderWidth: 2
        }]
      },
      options: {
        cutout: '70%',
        plugins: { legend: { display: true, position: 'bottom', labels: { color: '#64748b', font: { size: 14 } } } }
      }
    });

    // Team Workload Bar Chart
    const memberNames = [{% for m in project.team_members %}"{{ m }}"{% if not loop.last %},{% endif %}{% endfor %}];
    const memberCounts = [{% for m in project.team_members %}{{ tasks | selectattr('assignee', 'equalto', m) | list | length }}{% if not loop.last %},{% endif %}{% endfor %}];
    new Chart(document.getElementById('workloadChart').getContext('2d'), {
      type: 'bar',
      data: {
        labels: memberNames,
        datasets: [{ label: 'Tasks Assigned', data: memberCounts, backgroundColor: '#3b82f6', borderRadius: 8, maxBarThickness: 38 }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#64748b', font: { size: 13 } }, grid: { display: false } },
          y: { beginAtZero: true, ticks: { color: '#64748b', font: { size: 13 }, precision: 0 }, grid: { color: '#f1f5f9' } }
        }
      }
    });
  </script>
</body>
</html>"""


DEFAULT_USER_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{ user.name }} – Member Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --primary: #7c3aed;
      --secondary: #f1f5f9;
      --accent: #f59e42;
      --success: #22c55e;
      --danger: #ef4444;
      --card-bg: #fff;
      --text: #1e293b;
      --muted: #64748b;
      --shadow: 0 2px 16px 0 rgba(30,41,59,0.07);
      --border-radius: 16px;
      --gap: 2rem;
    }
    body {
      background: var(--secondary);
      font-family: 'Inter', Arial, sans-serif;
      color: var(--text);
      margin: 0;
      padding: 0;
      min-height: 100vh;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 2rem 1rem;
      display: flex;
      flex-direction: column;
      gap: var(--gap);
    }
    .dashboard-structure { display: flex; flex-direction: column; gap: var(--gap); }
    .header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 1rem; }
    .header-info { display: flex; flex-direction: column; gap: 0.5rem; }
    .user-title { font-size: 2.2rem; font-weight: 700; margin: 0; color: var(--primary); }
    .workspace-name { font-size: 1rem; color: var(--muted); font-weight: 500; }
    .user-email {
      font-size: 1rem; font-weight: 600; padding: 0.3em 1em;
      border-radius: 999px; background: var(--secondary);
      color: var(--primary); border: 1px solid var(--primary); display: inline-block;
    }
    .project-chips { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-top: 0.5rem; }
    .project-chip {
      background: var(--primary); color: #fff; border-radius: 999px;
      padding: 0.2em 0.9em; font-size: 0.88rem; font-weight: 500;
    }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1.5rem; }
    .kpi-card {
      background: var(--card-bg); border-radius: var(--border-radius);
      box-shadow: var(--shadow); padding: 1.5rem 1.2rem;
      display: flex; flex-direction: column; align-items: flex-start; gap: 0.5rem; min-width: 0;
    }
    .kpi-label { font-size: 1rem; color: var(--muted); font-weight: 500; }
    .kpi-value { font-size: 2.1rem; font-weight: 700; color: var(--text); margin-bottom: 0.25rem; }
    .kpi-rate { font-size: 1.1rem; font-weight: 600; color: var(--success); }
    .kpi-overdue { color: var(--danger); }
    .dashboard-sections { display: flex; flex-direction: column; gap: var(--gap); }
    .dashboard-row { display: flex; flex-wrap: wrap; gap: var(--gap); width: 100%; }
    .dashboard-col { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; gap: 1.5rem; }
    .charts-section { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 2rem; align-items: stretch; }
    .chart-card {
      background: var(--card-bg); border-radius: var(--border-radius);
      box-shadow: var(--shadow); padding: 1.5rem 1.2rem;
      display: flex; flex-direction: column; gap: 1rem; min-width: 0;
    }
    .chart-title { font-size: 1.1rem; font-weight: 600; color: var(--muted); margin-bottom: 0.5rem; }
    .tasks-section {
      background: var(--card-bg); border-radius: var(--border-radius);
      box-shadow: var(--shadow); padding: 1.5rem 1.2rem;
      margin-bottom: 2rem; overflow-x: auto;
    }
    .tasks-title { font-size: 1.3rem; font-weight: 700; margin-bottom: 1rem; color: var(--primary); }
    table.tasks-table { width: 100%; border-collapse: collapse; min-width: 750px; }
    table.tasks-table th, table.tasks-table td { padding: 0.75em 0.5em; text-align: left; }
    table.tasks-table th {
      color: var(--muted); font-size: 1rem; font-weight: 600;
      border-bottom: 2px solid var(--secondary); background: #f8fafc;
    }
    table.tasks-table tr { transition: background 0.15s; }
    table.tasks-table tr:hover { background: #f1f5f9; }
    table.tasks-table td { font-size: 1rem; border-bottom: 1px solid #f1f5f9; }
    .task-completed { color: var(--success); font-weight: 600; }
    .task-incomplete { color: var(--danger); font-weight: 600; }
    .task-tags { display: flex; gap: 0.3rem; flex-wrap: wrap; }
    .tag-badge {
      background: var(--accent); color: #fff; border-radius: 999px;
      padding: 0.15em 0.8em; font-size: 0.92rem; font-weight: 500;
    }
    @media (max-width: 900px) {
      .charts-section { grid-template-columns: 1fr; }
      .kpi-grid { grid-template-columns: 1fr 1fr; }
      .dashboard-row { flex-direction: column; }
    }
    @media (max-width: 600px) {
      .container { padding: 1rem 0.2rem; }
      .header { flex-direction: column; align-items: flex-start; gap: 0.7rem; }
      .kpi-grid { grid-template-columns: 1fr; }
    }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <div class="container">
    <div class="dashboard-structure">

      <!-- Header -->
      <div class="header">
        <div class="header-info">
          <div class="workspace-name">{{ workspace.name }}</div>
          <h1 class="user-title">{{ user.name }}</h1>
          <div style="display:flex; gap:1rem; flex-wrap:wrap; align-items:center; margin-top:0.5rem;">
            {% if user.email %}<span class="user-email">{{ user.email }}</span>{% endif %}
          </div>
          <div class="project-chips">
            {% for p in projects_contributed %}
              <span class="project-chip">{{ p }}</span>
            {% endfor %}
          </div>
        </div>
      </div>

      <div class="dashboard-sections">
        <!-- KPI Cards -->
        <div class="dashboard-row">
          <div class="dashboard-col">
            <div class="kpi-grid">
              <div class="kpi-card">
                <span class="kpi-label">Total Tasks</span>
                <span class="kpi-value">{{ summary.total_tasks }}</span>
              </div>
              <div class="kpi-card">
                <span class="kpi-label">Completed</span>
                <span class="kpi-value">{{ summary.completed_tasks }}</span>
              </div>
              <div class="kpi-card">
                <span class="kpi-label">Overdue</span>
                <span class="kpi-value kpi-overdue">{{ summary.overdue_tasks }}</span>
              </div>
              <div class="kpi-card">
                <span class="kpi-label">Completion Rate</span>
                <span class="kpi-value kpi-rate">{{ summary.completion_rate }}%</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Charts -->
        <div class="dashboard-row">
          <div class="dashboard-col">
            <div class="charts-section">
              <div class="chart-card">
                <div class="chart-title">Task Completion</div>
                <canvas id="completionChart"></canvas>
              </div>
              <div class="chart-card">
                <div class="chart-title">Projects Breakdown</div>
                <canvas id="projectsChart"></canvas>
              </div>
            </div>
          </div>
        </div>

        <!-- Tasks Table -->
        <div class="dashboard-row">
          <div class="dashboard-col">
            <div class="tasks-section">
              <div class="tasks-title">Tasks</div>
              <table class="tasks-table">
                <thead>
                  <tr>
                    <th>Task</th>
                    <th>Project</th>
                    <th>Due Date</th>
                    <th>Status</th>
                    <th>Tags</th>
                  </tr>
                </thead>
                <tbody>
                  {% for t in tasks %}
                  <tr>
                    <td>{{ t.name }}</td>
                    <td>{% if t.project %}{{ t.project }}{% else %}–{% endif %}</td>
                    <td>{% if t.due_date %}{{ t.due_date }}{% else %}–{% endif %}</td>
                    <td>
                      {% if t.completed %}
                        <span class="task-completed">Completed</span>
                      {% else %}
                        <span class="task-incomplete">Incomplete</span>
                      {% endif %}
                    </td>
                    <td>
                      <div class="task-tags">
                        {% for tag in t.tags %}
                          <span class="tag-badge">{{ tag }}</span>
                        {% endfor %}
                      </div>
                    </td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>

  <script>
    // Task Completion Doughnut
    new Chart(document.getElementById('completionChart').getContext('2d'), {
      type: 'doughnut',
      data: {
        labels: ['Completed', 'Incomplete'],
        datasets: [{
          data: [{{ summary.completed_tasks }}, {{ summary.incomplete_tasks }}],
          backgroundColor: ['#22c55e', '#ef4444'],
          borderWidth: 2
        }]
      },
      options: {
        cutout: '70%',
        plugins: { legend: { display: true, position: 'bottom', labels: { color: '#64748b', font: { size: 14 } } } }
      }
    });

    // Projects Breakdown Grouped Bar Chart
    new Chart(document.getElementById('projectsChart').getContext('2d'), {
      type: 'bar',
      data: {
        labels: [{% for p in projects_breakdown %}"{{ p.name }}"{% if not loop.last %},{% endif %}{% endfor %}],
        datasets: [
          {
            label: 'Total',
            data: [{% for p in projects_breakdown %}{{ p.total }}{% if not loop.last %},{% endif %}{% endfor %}],
            backgroundColor: '#7c3aed', borderRadius: 6, maxBarThickness: 28
          },
          {
            label: 'Completed',
            data: [{% for p in projects_breakdown %}{{ p.completed }}{% if not loop.last %},{% endif %}{% endfor %}],
            backgroundColor: '#22c55e', borderRadius: 6, maxBarThickness: 28
          },
          {
            label: 'Overdue',
            data: [{% for p in projects_breakdown %}{{ p.overdue }}{% if not loop.last %},{% endif %}{% endfor %}],
            backgroundColor: '#ef4444', borderRadius: 6, maxBarThickness: 28
          }
        ]
      },
      options: {
        plugins: { legend: { display: true, position: 'bottom', labels: { color: '#64748b', font: { size: 13 } } } },
        scales: {
          x: { ticks: { color: '#64748b', font: { size: 12 } }, grid: { display: false } },
          y: { beginAtZero: true, ticks: { color: '#64748b', font: { size: 12 }, precision: 0 }, grid: { color: '#f1f5f9' } }
        }
      }
    });
  </script>
</body>
</html>"""
