// Função para alternar o menu de navegação em dispositivos móveis
function toggleMenu() {

        document.getElementById ("navLinks") .classList.toggle ("active");

    }

    document.querySelectorAll(".nav-links a").forEach(link => {
        
        link.addEventListener("click", () => {
            
            document.getElementById("navLinks").classList.remove("active");
        });
    });

// Função para rolar suavemente até o iframe de contato
function scrollParaIframe() {
    setTimeout(() => {
        document
            .getElementById("iframe-contato")
            .scrollIntoView({ behavior: "smooth", block: "start" });
    }, 300);
}

// Adiciona destaque sutil aos números diferentes de zero na tabela
  document.querySelectorAll('.tabela-projetos td').forEach(td => {
    const valor = td.textContent.trim();
    if (valor !== '0' && valor !== '') {
      td.style.color = '#b30000';
      td.style.fontWeight = 'bold';
    }
  });