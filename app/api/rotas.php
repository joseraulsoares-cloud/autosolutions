<?php
declare(strict_types=1);

// Encaminhamento da API. Só usa GET e POST, para não esbarrar nas regras de segurança dos alojamentos partilhados.

const ROTAS = [
    ['GET', '#^/sessao$#', 'api_sessao'],
    ['POST', '#^/sessao/sair$#', 'api_sair'],
    ['POST', '#^/entrar/codigo$#', 'api_entrar_codigo'],
    ['POST', '#^/entrar/verificar$#', 'api_entrar_verificar'],
    ['POST', '#^/registo$#', 'api_registo'],
    ['GET', '#^/conta$#', 'api_conta'],
    ['POST', '#^/conta$#', 'api_conta_guardar'],
    ['GET', '#^/saldo$#', 'api_saldo'],
    ['GET', '#^/pedidos$#', 'api_pedidos'],
    ['POST', '#^/pedidos$#', 'api_pedido_criar'],
    ['GET', '#^/pedidos/(\d+)$#', 'api_pedido'],
    ['POST', '#^/pedidos/(\d+)/cancelar$#', 'api_pedido_cancelar'],
    ['POST', '#^/pedidos/(\d+)/original$#', 'api_pedido_original_enviar'],
    ['GET', '#^/pedidos/(\d+)/(original|modificado)$#', 'api_pedido_ficheiro'],
    ['GET', '#^/admin/resumo$#', 'api_admin_resumo'],
    ['GET', '#^/admin/pedidos$#', 'api_admin_pedidos'],
    ['GET', '#^/admin/pedidos/(\d+)$#', 'api_admin_pedido'],
    ['POST', '#^/admin/pedidos/(\d+)/estado$#', 'api_admin_pedido_estado'],
    ['POST', '#^/admin/pedidos/(\d+)/modificado$#', 'api_admin_pedido_modificado'],
    ['POST', '#^/admin/pedidos/(\d+)/custo$#', 'api_admin_pedido_custo'],
    ['GET', '#^/admin/oficinas$#', 'api_admin_oficinas'],
    ['GET', '#^/admin/oficinas/(\d+)$#', 'api_admin_oficina'],
    ['POST', '#^/admin/oficinas/(\d+)/estado$#', 'api_admin_oficina_estado'],
    ['POST', '#^/admin/oficinas/(\d+)/tokens$#', 'api_admin_oficina_tokens'],
    ['POST', '#^/admin/oficinas/(\d+)/dados$#', 'api_admin_oficina_dados'],
    ['POST', '#^/admin/oficinas/(\d+)/apagar$#', 'api_admin_oficina_apagar'],
    ['POST', '#^/contacto$#', 'api_contacto'],
    ['GET', '#^/dev/emails$#', 'api_dev_emails'],
];

function caminho_api(): string
{
    $caminho = (string) (parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/');
    $pos = strpos($caminho, '/api/');
    $resto = $pos === false ? '' : substr($caminho, $pos + 4);
    return '/' . trim($resto, '/');
}

function garc_api_executar(): void
{
    $metodo = $_SERVER['REQUEST_METHOD'] ?? 'GET';
    $caminho = caminho_api();
    try {
        if ($metodo === 'POST') {
            verificar_origem();
        }
        $existe = false;
        foreach (ROTAS as [$m, $padrao, $funcao]) {
            if (!preg_match($padrao, $caminho, $partes)) {
                continue;
            }
            $existe = true;
            if ($m !== $metodo) {
                continue;
            }
            array_shift($partes);
            $r = $funcao(...$partes);
            if ($r instanceof Resposta) {
                responder_json($r->dados, $r->status);
            } elseif (is_array($r)) {
                responder_json($r);
            }
            executar_depois();
            return;
        }
        throw new ErroHttp($existe ? 405 : 404, $existe ? 'Método não permitido.' : 'Endereço desconhecido.');
    } catch (ErroHttp $e) {
        responder_json(['erro' => $e->getMessage()] + $e->extra, $e->status);
    } catch (Throwable $e) {
        error_log('GARC API: ' . $e);
        responder_json(['erro' => 'Erro interno. Tente de novo dentro de momentos.'], 500);
    }
}
