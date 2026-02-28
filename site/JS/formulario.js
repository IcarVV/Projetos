class FormSubmit { 

    constructor(settings) {
        this.settings = settings;
        this.form = document.querySelector(settings.form);

        if (this.form) {
            this.url = this.form.getAttribute('action');
        }

        this.sendForm = this.sendForm.bind(this);
    }

    displaySuccess(){
        this.form.innerHTML = this.settings.success;
    }

    displayError(){
        this.form.innerHTML = this.settings.error;
    }

    async sendForm(event) {
        event.preventDefault();

        const button = this.form.querySelector('[data-button]');

        if (!this.form.checkValidity()) {
            this.form.reportValidity();
            return;
        }

        button.disabled = true;
        button.innerText = 'Enviando...';

        try {
            const formData = new FormData(this.form);

            const response = await fetch(this.url, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error();

            this.displaySuccess();
        
        } catch (error) {
            this.displayError();
        }
    }

    init() {
        if (this.form) {
            this.form.addEventListener('submit', this.sendForm);
        }
        return this;
    }
}

const formSubmit = new FormSubmit({
    form: '[data-form]',
    success: '<h1 class="success">Mensagem enviada com sucesso!</h1>' + '<br>' + '<a href="/Formulario">_Voltar</a>',
    error: '<h1 class="error">Não foi possível enviar a mensagem.</h1>'
});

formSubmit.init();