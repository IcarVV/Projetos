<?php

require_once 'config.php';

//pegando os dados do formulário

if ( isset($_POST['Nome'])) {

    $Nome = $_POST['Nome'];

}

if ( isset($_POST['Email'])) {

    $Email = $_POST['Email'];

}

if ( isset($_POST['Mensagem'])) {

    $Mensagem = $_POST['Mensagem'];

}

$data_atual = date("d/m/Y");

$hora_atual = date("H:i:s");

//inserindo os dados no banco de dados
$smtp = $conn->prepare("INSERT INTO mensagens (Nome, Email, Mensagem, Data, Hora) VALUES (?, ?, ?, ?, ?)");

//ligando os parâmetros
$smtp->bind_param("sssss", $Nome, $Email, $Mensagem, $data_atual, $hora_atual);


//verificando se a execução foi bem sucedida
if ($smtp->execute()) {

    echo "Mensagem enviada com sucesso!";

} else {

    echo "Erro ao enviar a mensagem: " . $smtp->error;

}

//fechando a conexão
$smtp->close();
$conn->close();

?>