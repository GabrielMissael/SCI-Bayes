import numpy as np
from coupling_coefficients import *
from numpy.polynomial.polynomial import polyval
import scipy.optimize as op


#class with the 21cm signal parametrizations
class model_21cm(object):
    def __init__(self, freq, model_type='gaussian'):
        self.freqs = freq
        self.model = model_type

    def __call__(self, *pars):
        """
        Definicion de la parametrizacion Gaussiana
        T_0, nu, sigma: parametros de entrada
        Tb: salida
            """
        if self.model == 'gaussian':
            T, nu, sigma = pars
            T_b = -T * np.exp(-(nu - self.freqs)**2 / 2. / sigma**2)
            return T_b

        elif self.model == 'tanh':
            """
            Definicion de la parametrizacion tanh
            """
            logx0, xz, xdz, logT0, Tz, Tdz, J0, Jz, Jdz = pars

            v_0=1420.4057
            z = v_0 / self.freqs - 1.
            T_cmb = 2.725 * (1. + z)
            Tg = T_cmb * ((1. + z) / (1. + 150.))**2

            x0 = 10.**logx0
            T0 = 10.**logT0

            x_par = 0.5 * x0 * (np.tanh((xz - z) / xdz) + 1.)
            T_par = 0.5 * T0 * (np.tanh((Tz - z) / Tdz) + 1.) + Tg
            J_par = 0.5 * J0 * (np.tanh((Jz - z) / Jdz) + 1.)

            J_par *= 1e-12

            cc=CouplingCoefficients()
            x_c = cc.CollisionalCouplingCoefficient(z,T_par)
            x_a = cc.RadiativeCouplingCoefficient(z,J_par)

            T_s = (1. + x_c + x_a) / (T_cmb**-1. + x_c * T_par**-1. + x_a * T_par**-1.)

            dTb = 27.0 * (1. - x_par) * np.sqrt(( 1. + z) / 10.) * (1. - T_cmb / T_s)
            return dTb


#class with the foreground model (log not base 10 log)
class foreground(object):
    """
    Definicion del foreground
    freq: las frecuencias de observacion
    c_i: coeficientes de la expancion polinomial
    """
    def __init__(self, freq):
        self.freqs = freq

    def __call__(self, *pars):
        c0, c1, c2, c3 = pars
        params1 = np.array([c0, c1, c2, c3])
        T_gx = np.exp(polyval(np.log(self.freqs / 80.), params1))
        #el valor central (80) se debe de cambiar dependiendo el rango de freqs
        return T_gx

def radiometer(Tsys, tint, channel):
    """
    Funcion para calcular sigma
    Tsys: temperatura observada
    tinit: tiempo de observacion.
    channel: binning de frecuencias
    """
    hz_per_mhz = 1e6
    s_per_hr = 3600.

    x = Tsys / np.sqrt(tint * s_per_hr * channel * hz_per_mhz)

    return x

# the functions needed for emcee taking in to account the priors

#first we define the likelihood function for each parametrization


def lnhood(pars, model, T_sky, freqs, err):
    """
    Logaritmo del Likelihood.
    pars: parametros de la temperatura de brillo y el foreground
    model: gaussian o tanh.
    T_sky: temperatura observada.
    freqs: frecuencias medidas.
    err: sigma,
    """
    if model == 'gaussian':
        signal_pars = pars[:3]
        fore_pars = pars[3:]

        #se llaman las clases con las parametrizaciones
        signal = model_21cm(freqs, model)
        fore = foreground(freqs)

        Tb = signal(signal_pars[0], signal_pars[1], signal_pars[2]) * 1e-3
        Tgx = fore(fore_pars[0], fore_pars[1], fore_pars[2])
        T_model = Tb + Tgx

        p = (((T_sky - T_model) / err)**2) + np.log(2. * np.pi * err**2)
        return -0.5 * np.sum(p)

    elif model == 'tanh':
        signal_pars = pars[:9]
        fore_pars = pars[9:]

        signal = model_21cm(freqs, model)
        fore = foreground(freqs)

        Tb = signal(signal_pars[0], signal_pars[1], signal_pars[2],\
                    signal_pars[3], signal_pars[4], signal_pars[5],\
                    signal_pars[6],signal_pars[7],signal_pars[8]) * 1e-3
        Tgx = fore(fore_pars[0],fore_pars[1], fore_pars[2], fore_pars[3])
        T_model = Tb + Tgx

        p = (((T_sky - T_model) / err)**2) + np.log(2. * np.pi * err**2)
        return -0.5 * np.sum(p)


def priors(pars, lists, model):
    """
    Funcion de probabilidad a priori.
    lists: Lista de limites para los posibles valores de los params.
    """
    if model == 'gaussian':
        if lists[0]<pars[0]<lists[1] and lists[2]<pars[1]<lists[3] and\
         lists[4]<pars[2]<lists[5] and lists[6]<pars[3]<lists[7] and\
         lists[8]<pars[4]<lists[9] and lists[10]<pars[5]<lists[11]:
            return 0.0
        return -np.inf


    elif model == 'tanh':
        logx0, xz, xdz, logT0, Tz, Tdz, J0, Jz, Jdz,c0,c1,logc2,logc3 = pars
        if lists[0]<logx0<lists[1] and lists[2]<xz<lists[3] and\
         lists[4]<xdz<lists[5] and lists[6]<logT0<lists[7] and\
         lists[8]<Tz<lists[9] and lists[10]<Tdz<lists[11] and\
         lists[12]<J0<lists[13] and lists[14]<Jz<lists[15] and\
         lists[16]<Jdz<lists[17] and lists[18]<c0<lists[19] and\
         lists[20]<c1<lists[21] and lists[22]<logc2<lists[23] and\
         lists[24]<logc3<lists[25]:
            return 0.0
        return -np.inf

#por si se tiene un prior informativo. Este caso es para los params del foreground
#def Gauss_priors(pars, mu):

#    fore_pars = pars[9:]
#    sigma = 2.

#    gauss_1 = -0.5 * (fore_pars[0] - mu[0])**2 / sigma**2
#    gauss_2 = -0.5 * (fore_pars[1] - mu[1])**2 / sigma**2
#    gauss_3 = -0.5 * (fore_pars[2] - mu[2])**2 / sigma**2

#    total = gauss_1 + gauss_2 + gauss_3
#    return total

#flat = flat_priors(pars, lists)
#gauss = Gauss_priors(pars, mu)
#return flat + gauss

def log_posterior(pars, model, T_sky, freqs, err, lists):
    p = priors(pars, lists,model)
    if not np.isfinite(p):
        return -np.inf
    return p + lnhood(pars, model, T_sky, freqs, err)
