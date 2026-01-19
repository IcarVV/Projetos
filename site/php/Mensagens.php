<?php

require_once 'config.php';

$senhaCorreta = "admin123";
$result = null;
$erro = '';

// Verifica se o formulário foi submetido
if ($_SERVER["REQUEST_METHOD"] === "POST") {

    $senhadigitada = $_POST['senha'] ?? '';

    // Verifica se a senha está correta
    if ($senhadigitada === $senhaCorreta) {

        $sql = "SELECT * FROM mensagens";
        $result = $conn->query($sql);

    } else {
        echo "<h1>Senha incorreta. Acesso negado.</h1>";

        $erro = "Senha incorreta. Acesso negado.";
    }
}
?>

<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/CSS/styles.css">
    <title>Ver mensagens</title>
</head>
<body>

    <form method="post" action="/site/php/Mensagens.php">
        <label for="senha">Senha:</label>
        <input type="password" id="senha" name="senha" placeholder="Digite sua senha" required>
        <input type="submit" value="Ver Mensagens">
    </form>

    <?php if (isset ($result) && $result->num_rows > 0) : ?>

        <ul>
            <?php while($row = $result->fetch_assoc()) : ?>
                <li class="lista-mensagem">
                
                        <strong>Nome:</strong> <?php echo $row ['Nome']; ?> <br>
                        <strong>Email:</strong> <?php echo $row ['Email']; ?> <br>
                        <strong>Mensagem:</strong> <?php echo $row ['Mensagem']; ?> <br>
                        <strong>Data e Hora:</strong> <span class="data-hora"> <?= htmlspecialchars($row['Data'] . " às " . $row['Hora']) ?> </span>
                </li>
            
            <?php endwhile; ?>
        </ul>

    <?php else : ?>
        <p>Nenhuma mensagem encontrada.</p>
    <?php endif; ?>
    
</body>

</html>