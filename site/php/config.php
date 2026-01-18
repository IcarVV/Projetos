<?php

//conexão com o banco de dados
$conn = new mysqli ('localhost', 'root', '', 'formulario');

//verificando a conexão
if ($conn->connect_error) {

    die("Conexão falhou: " . $conn->connect_error);

}

?>