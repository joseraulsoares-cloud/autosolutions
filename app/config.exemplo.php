<?php
// Copie este ficheiro para config.php, na mesma pasta, e preencha os valores.
// O config.php tem palavras-passe e não entra no repositório.
return [
    // Base de dados MySQL criada no cPanel (MySQL Database Wizard)
    'db' => [
        'host' => 'localhost',
        'nome' => 'UTILIZADOR_garc',
        'utilizador' => 'UTILIZADOR_garc',
        'palavra_passe' => '',
    ],

    // Endereço público do site, sem barra no fim
    'site_url' => 'https://www.autosolutions.pt',

    // Nome usado nos emails enviados pelo site
    'nome' => 'GARC – Soluções Técnicas',

    // Emails com acesso ao painel de administração, separados por vírgulas
    'admin_emails' => '',

    // Remetente dos emails (conta de email criada no cPanel)
    'email_de' => 'GARC – Soluções Técnicas <pedidos@autosolutions.pt>',

    // Destino das mensagens do formulário de contacto (vazio = primeiro email de administração)
    'email_contacto' => '',

    // Pasta dos ficheiros das oficinas, fora de public_html
    'ficheiros_dir' => '/home/UTILIZADOR/autosolutions-dados/ficheiros',

    // Texto aleatório com 64 caracteres ou mais, usado para proteger os códigos de acesso
    'segredo' => '',

    // Ficheiros até este tamanho seguem em anexo nos emails; acima disso, o email leva só o aviso
    'anexo_max_mb' => 15,

    // Desenvolvimento: os emails ficam na tabela emails_dev em vez de serem enviados. Nunca ativar no alojamento.
    'dev' => false,
];
