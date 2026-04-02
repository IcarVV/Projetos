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

// Destaca o link ativo na navegação

document.addEventListener("DOMContentLoaded", () => {
  const links = document.querySelectorAll(".nav-links a");

  // remove index.html e barra final
  const normalize = (path) =>
    path.replace("index.html", "").replace(/\/$/, "");

  const currentPath = normalize(window.location.pathname);

  links.forEach(link => {
    const linkPath = normalize(new URL(link.href).pathname);

    if (currentPath === linkPath) {
      link.classList.add("active");
    }
  });
});