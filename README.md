# Studio Batucada - Sistema de Gestão de Aulas

[![Python Version](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/Django-5.x-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Sistema de gestão completo para escolas de música, focado em otimizar o fluxo de trabalho de administradores e professores através de dashboards inteligentes, relatórios visuais e uma interface interativa e moderna.

![Dashboard Principal do Sistema](caminho/para/seu/screenshot_dashboard.png)
_Dashboard principal com o calendário interativo e KPIs da visão do administrador._

## Visão Geral

O "Studio Batucada" é uma aplicação web robusta que centraliza e simplifica o gerenciamento de aulas, alunos, professores e modalidades. Construído com Django, o sistema vai além de um simples CRUD, oferecendo dashboards analíticos, ferramentas de visualização de dados e fluxos de trabalho inteligentes, como o de substituição de professores, para atender às necessidades dinâmicas de uma escola de música moderna.

## Funcionalidades Principais

### 1. Dashboards Analíticos e Contextuais
O sistema oferece dashboards personalizados para cada tipo de usuário, fornecendo as informações mais relevantes de forma rápida e visual.

* **Dashboard do Admin:** Visão 360º da escola com KPIs (Aulas Hoje, Aulas na Semana), calendário completo com filtro por professor e listas de atividades diárias e semanais.
* **Dashboard do Professor:** Painel pessoal com métricas de desempenho (Aulas Realizadas, Taxa de Presença, Substituições), calendário focado em suas próprias aulas e uma lista de tarefas "Aulas Pendentes de Validação".
* **Perfis de Aluno e Modalidade:** Cada aluno e modalidade possuem suas próprias páginas de detalhe, transformadas em dashboards com estatísticas, gráficos de atividade e históricos completos.

    ![Dashboard do Professor](caminho/para/seu/screenshot_professor_detalhe.png)
    _Exemplo do dashboard de um professor, com KPIs, gráficos e listas de Top Alunos/Modalidades._

### 2. Agendamento Inteligente e Interativo
* **Calendário FullCalendar:** Um calendário visual e interativo é o centro do dashboard. Eventos são coloridos por status e exibem informações detalhadas em um popover ao passar o mouse.
* **Verificação de Conflito em Tempo Real (AJAX):** O formulário de agendamento impede agendamentos duplos, consultando a disponibilidade do professor em tempo real sem precisar recarregar a página.
* **Agendamento Recorrente:** Opção para agendar aulas recorrentes para todo o mês com um único clique.

### 3. Relatórios e Listagens Enriquecidas
* **Listagens Inteligentes:** As páginas de listagem de Aulas, Alunos, Professores e Modalidades foram aprimoradas com barras de busca e colunas de dados agregados (ex: "Total de Aulas", "Próxima Aula"), calculados de forma eficiente com o `annotate` do Django.
* **Relatórios Gerais:** Uma página de relatórios poderosa com filtros avançados (data, professor, modalidade, status) que atualizam os KPIs, tabelas agregadas e gráficos em tempo real.
* **Exportação para CSV:** Funcionalidade que permite ao admin exportar dados filtrados das listas e relatórios para arquivos CSV.

    ![Relatórios Dinâmicos](caminho/para/seu/gif_relatorios.gif)
    _Filtros avançados e gráficos sendo atualizados na página de relatórios._

### 4. Validação de Aulas e Fluxo de Substituição
* **Relatórios de Aula Dinâmicos:** Professores validam aulas preenchendo relatórios detalhados com `formsets` dinâmicos, permitindo adicionar múltiplos exercícios de forma interativa.
* **Lógica de Substituição Contextual:** O sistema identifica visualmente quando uma aula foi ministrada por um professor substituto. A interface se adapta para mostrar a informação mais relevante dependendo de quem está visualizando o histórico (o professor que substituiu, o que foi substituído ou um admin).

## Tecnologias Utilizadas

* **Backend:** Python 3.x, Django 5.x, SQLite
* **Frontend:** HTML5, CSS3, JavaScript (ES6), Bootstrap 5, Bootstrap Icons
* **Bibliotecas JS:** Chart.js, FullCalendar v6, Flatpickr
* **Autenticação:** `django.contrib.auth` (com `CustomUser`), `django-allauth` para login social com Google.
* **Outros:** `python-decouple` para variáveis de ambiente.

## Configuração do Ambiente

### Pré-requisitos
* Python 3.8+
* `pip` e `venv`

### Instalação
1.  **Clone o repositório:** `git clone [URL_DO_SEU_REPOSITORIO]`
2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    # Windows: .\venv\Scripts\activate | macOS/Linux: source venv/bin/activate
    ```
3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuração de Variáveis de Ambiente
1.  No diretório raiz, crie um arquivo chamado `.env`.
2.  Adicione as seguintes variáveis, substituindo pelos seus valores:
    ```ini
    SECRET_KEY=sua_chave_secreta_super_segura_aqui
    DEBUG=True
    GOOGLE_CLIENT_ID=seu_id_de_cliente_do_google
    GOOGLE_SECRET_KEY=sua_chave_secreta_do_google
    ```

### Configuração Google OAuth (Login Social)
1.  Acesse o [Google Cloud Console](https://console.cloud.google.com/) e crie um projeto.
2.  Vá para "APIs & Services" > "Credentials" e crie uma "OAuth client ID" do tipo "Web application".
3.  Em "Authorized redirect URIs", adicione:
    * `http://127.0.0.1:8000/accounts/google/login/callback/`
    * `http://localhost:8000/accounts/google/login/callback/`
4.  Copie o Client ID e o Client Secret para o seu arquivo `.env`.
5.  No Admin do Django (`/admin`), vá em "Social Applications", adicione uma nova aplicação "Google" e cole o Client ID e Secret novamente.

### Banco de Dados e Superusuário
1.  **Execute as migrações:** `python manage.py migrate`
2.  **Crie um superusuário:** `python manage.py createsuperuser`

## Como Executar o Projeto
```bash
python manage.py runserver

Acesse a aplicação em http://127.0.0.1:8000/.
```

## Melhorias Futuras (Roadmap)

- [ ] **Métricas Financeiras:** Adicionar um campo de `valor` às aulas para calcular faturamento por período, professor ou modalidade.
- [ ] **Notificações:** Implementar um sistema de e-mails para avisar professores sobre novas aulas ou cancelamentos.
- [ ] **Portal do Aluno:** Criar uma área de login para o aluno, onde ele possa ver seu cronograma de aulas, seu progresso e o histórico de relatórios.
- [ ] **Gráficos Interativos:** Permitir que o clique em uma barra do gráfico (ex: "Aulas Realizadas") filtre a tabela de histórico abaixo.

## Licença

Distribuído sob a Licença MIT. Veja o arquivo `LICENSE` para mais informações.